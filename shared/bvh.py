#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Jonas Hauquier, Marc Flerackers, Thomas Larsson

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

BVH motion capture file parser.
Allows parsing joint skeleton structures and accompanying motion data, and
transforming them into bone-based skeletons for use with skeletal animation.
"""

import skeleton
import animation
import log

import numpy as np
import transformations as tm
import numpy.linalg as la

from math import pi
D = pi/180


class BVH():
    """
    A BVH skeleton. We assume a single root joint.
    This skeleton allows access to both joints and bones.
    """
    def __init__(self):
        self.joints = {}    # Lookup dict to find joints by name
        self.bvhJoints = [] # List of joints in the order in which they were defined in the BVH file (important for MOTION data parsing)
        self.jointslist = []    # Cached breadth-first list of all joints
        self.rootJoint = None   # TODO we assume only one root joint. Useful to allow multiple? (BVH spec allows multiple roots in theory)

        self.frameTime = -1
        self.frames = []

        self.convertFromZUp = False     # Set to true to convert the coordinates from a Z-is-up coordinate system. Most motion capture data uses Y-is-up, though.

    def addRootJoint(self, name):
        self.rootJoint = self.__addJoint(name)
        return self.rootJoint

    def addJoint(self, parentName, name):
        origName = name
        i = 1
        while name in list(self.joints.keys()):
            name = "%s_%s" % (origName, i)
            i = i+1
        parent = self.getJoint(parentName)
        joint = self.__addJoint(name)
        parent.addChild(joint)
        return joint

    def __addJoint(self, name):
        joint = BVHJoint(name, self)
        if joint.name != "End effector":
            self.joints[name] = joint
        self.bvhJoints.append(joint)
        return joint

    def createSkeleton(self, onlyFirstChildToBone=False, hidePrefix="_"):
        """
        Convert BVH joint rig to bone skeleton. A bone-based skeleton has the
        feature that bones don't need to be connected, and can be offset from
        each other, without the need of dummy joints (for example with a hide
        prefix) or joints with multiple children.
        If onlyFirstChildToBone is true, if a joint has multiple children, a
        bone will only be created between the parent joint and the first child.
        Joint names that start with the hidePrefix substring (often "_" or 
        "dummy") do not get converted to a bone.
        Set hidePrefix to None or empty string to disable bone hiding.
        """
        skel = skeleton.Skeleton("BVHSkeleton")

        # Traverse joints in breadth-first order
        for joint in self.getJoints():
            if joint.hasParent():
                parent = joint.parent
                if hidePrefix and parent.name.startswith(hidePrefix):
                    # Parent joint's name has hide prefix Skip/don't create bone
                    continue
                if onlyFirstChildToBone and parent.children[0] != joint:
                    # Joint is not first child: Skip/don't create bone
                    continue

                boneName = parent.name
                # Assign a unique name to bone
                if skel.containsBone(boneName):
                    postIdx = 1
                    while skel.containsBone(boneName):
                        boneName = "%s_%s" % (parent.name, postIdx)
                        postIdx = postIdx + 1

                # TODO this code would be simpler if we assigned joint objects to bones
                if parent.parent:
                    joint_ = parent.parent
                    parentBoneName = joint_.name
                    # When bone is hidden, choose parent joint as parent bone
                    while hidePrefix and parentBoneName and parentBoneName.startswith(hidePrefix):
                        if joint_.parent:
                            joint_ = joint_.parent
                            parentBoneName = joint_.name
                        else:
                            parentBoneName = None
                else:
                    parentBoneName = None

                # Create a bone between joint and its parent
                skel.addBone(boneName, parentBoneName, parent.position, joint.position)

        skel.build()
        skel.update()
        return skel

    # TODO guess source armature from a BVH rig

    def createAnimationTrack(self, jointsOrder = None, name="BVHMotion"):
        """
        Create an animation track from the motion stored in this BHV file.
        """
        if jointsOrder == None:
            jointsData = [joint.matrixPoses for joint in self.getJoints() if not joint.isEndConnector()]
            # We leave out end effectors as they should not have animation data
        else:
            nFrames = self.frameCount
            import re
            # Remove the tail from duplicate bone names
            for idx,jName in enumerate(jointsOrder):
                # Joint mappings can contain a rotation compensation
                if isinstance(jName, tuple):
                    jName, _ = jName
                if not jName:
                    continue
                r = re.search("(.*)_\d+$",jName)
                if r:
                    jointsOrder[idx] = r.group(1)

            jointsData = []
            for jointName in jointsOrder:
                if isinstance(jointName, tuple):
                    jointName, angle = jointName
                else:
                    angle = 0.0
                if jointName:
                    poseMats = self.getJointByCanonicalName(jointName).matrixPoses.copy()
                    if isinstance(angle, float):
                        if angle != 0.0:
                            # Rotate around global Z axis
                            rot = tm.rotation_matrix(-angle*D, [0,0,1])
                            # Roll around global Y axis (this is a limitation)
                            roll = tm.rotation_matrix(angle*D, [0,1,0])
                            for i in range(nFrames):
                                # TODO make into numpy loop
                                poseMats[i] = np.dot(poseMats[i], rot)
                                poseMats[i] = np.dot(poseMats[i], roll)
                    else:   # Compensation (angle) is a transformation matrix
                        # Compensate animation frames
                        for i in range(nFrames):
                            # TODO make into numpy loop
                            poseMats[i] = np.mat(poseMats[i]) * np.mat(angle)
                            #poseMats[i] = np.mat(angle) # Test compensated rest pose
                    jointsData.append(poseMats)
                else:
                    jointsData.append(animation.emptyTrack(nFrames))

        nJoints = len(jointsData)
        nFrames = len(jointsData[0])

        # Interweave joints animation data, per frame with joints in breadth-first order
        animData = np.hstack(jointsData).reshape(nJoints*nFrames,4,4)
        framerate = 1.0/self.frameTime
        return animation.AnimationTrack(name, animData, nFrames, framerate)

    def getJoint(self, name):
        return self.joints[name]

    def getJointByCanonicalName(self, canonicalName):
        canonicalName = canonicalName.lower().replace(' ','_').replace('-','_')
        for jointName in [ name for name in list(self.joints.keys())]:
            if canonicalName == jointName.lower().replace(' ','_').replace('-','_'):
                return self.getJoint(jointName)
        return None

    def containsJoint(self, name):
        return name in self.joints

    def __cacheGetJoints(self):
        from queue import deque

        result = []
        queue = deque([self.rootJoint])
        while len(queue) > 0:
            joint = queue.popleft()
            result.append(joint)
            queue.extend(joint.children)
        self.jointslist = result
        
    def getJoints(self):
        """
        Returns linear list of all joints in breadth-first order.
        """
        return self.jointslist

    def getJointsBVHOrder(self):
        """
        Retrieve joints as they were ordered in the BVH hierarchy definition.
        """
        return self.bvhJoints

    def fromFile(self, filepath):
        """
        Parse a BVH skeletal animation file.
        Loads both the skeleton hierarchy and the animation track from the 
        specified BVH file.
        """
        fp = open(filepath, "rU")

        # Read hierarchy
        self.__expectKeyword('HIERARCHY', fp)
        words = self.__expectKeyword('ROOT', fp)
        rootJoint = self.addRootJoint(words[1])        

        self.__readJoint(self.rootJoint, fp)

        # Read motion
        self.__expectKeyword('MOTION', fp)

        words = self.__expectKeyword('Frames:', fp)
        self.frameCount = int(words[1])
        words = self.__expectKeyword('Frame', fp) # Time:
        self.frameTime = float(words[2])

        for i in range(self.frameCount):
            line = fp.readline()
            words = line.split()
            data = [float(word) for word in words]
            for joint in self.getJointsBVHOrder():
                data = self.__processChannelData(joint, data)

        self.__cacheGetJoints()

        # Transform frame data into transformation matrices for all joints
        for joint in self.getJoints():
            joint.calculateFrames()     # TODO we don't need to calculate pose matrices for end effectors

    def fromSkeleton(self, skel, animationTrack = None, dummyJoints = True):
        """
        Construct a BVH object from a skeleton structure and optionally an 
        animation track. If no animation track is specified, a dummy animation
        of one frame will be added.
        If dummyJoints is true (the default) then extra dummy joints will be
        introduced when bones are not directly connected, but have their head
        position offset from their parent bone tail. This often happens when
        multiple bones are attached to one parent bones, for example in the
        shoulder, hip and hand areas.
        When dummyJoints is set to false, for each bone in the skeeton, exactly
        one BVH joint will be created. How this is interpreted depends on the
        tool importing the BVH file. Some create only a bone between the parent
        and its first child joint, and create empty offsets to the other childs.
        Other tools create one bone, with the tail position being the average
        of all the child joints. Dummy joints are introduced to prevent 
        ambiguities between tools. Dummy joints carry the same name as the bone
        they parent, with "__" prepended.

        NOTE: Make sure that the skeleton has only one root.
        """

        # Traverse skeleton joints in depth-first order
        for jointName in skel.getJointNames():
            bone = skel.getBone(jointName)
            if dummyJoints and bone.parent and \
               (bone.getRestHeadPos() != bone.parent.getRestTailPos()).any():
                # Introduce a dummy joint to cover the offset between two not-
                # connected bones
                joint = self.addJoint(bone.parent.name, "__"+jointName)
                joint.channels = ["Zrotation", "Xrotation", "Yrotation"]
                parentName = joint.name

                offset = bone.parent.getRestTailPos() - bone.parent.getRestHeadPos()
                self.__calcPosition(joint, offset)
                offset = bone.getRestHeadPos() -  bone.parent.getRestTailPos()
            else:
                parentName = bone.parent.name if bone.parent else None
                offset = bone.getRestOffset()

            if bone.parent:
                joint = self.addJoint(parentName, jointName)
                joint.channels = ["Zrotation", "Xrotation", "Yrotation"]
            else:
                # Root bones have translation channels
                joint = self.addRootJoint(bone.name)
                joint.channels = ["Xposition", "Yposition", "Zposition", "Zrotation", "Xrotation", "Yrotation"]
    
            self.__calcPosition(joint, offset)
            if not bone.hasChildren():
                endJoint = self.addJoint(jointName, 'End effector')
                offset = bone.getRestTailPos() - bone.getRestHeadPos()
                self.__calcPosition(endJoint, offset)

        self.__cacheGetJoints()
        nonEndJoints = [ joint for joint in self.getJoints() if not joint.isEndConnector() ]

        if animationTrack:
            self.frameCount = animationTrack.nFrames
            self.frameTime = 1.0/animationTrack.frameRate

            jointToBoneIdx = {}
            for joint in nonEndJoints:
                if skel.containsBone(joint.name):
                    jointToBoneIdx[joint.name] = skel.getBone(joint.name).index
                else:
                    jointToBoneIdx[joint.name] = -1

            for fIdx in range(animationTrack.nFrames):
                offset = fIdx * animationTrack.nBones
                for jIdx,joint in enumerate(nonEndJoints):
                    bIdx = jointToBoneIdx[joint.name]
                    if bIdx < 0:
                        poseMat = np.identity(4, dtype=np.float32)
                    else:
                        poseMat = animationTrack.data[offset + bIdx]

                    if len(joint.channels) == 6:
                        # Add transformation
                        tx, ty, tz = poseMat[:3,3]
                        joint.frames.extend([tx, ty, tz])
                    ay,ax,az = tm.euler_from_matrix(poseMat, "syxz")
                    joint.frames.extend([az/D, ax/D, ay/D])
        else:
            # Add bogus animation with one frame
            self.frameCount = 1
            self.frameTime = 1.0
            for jIdx,joint in enumerate(nonEndJoints):
                if len(joint.channels) == 6:
                    # Add transformation
                    joint.frames.extend([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
                else:
                    joint.frames.extend([0.0, 0.0, 0.0])

        for joint in self.getJoints():
            joint.calculateFrames()

    def writeToFile(self, filename):
        """
        Write this BVH structure to a file.
        """
        f = open(filename, 'w')

        # Write structure
        f.write('HIERARCHY\n')
        self._writeJoint(f, self.rootJoint, 0)

        # Write animation
        f.write('MOTION\n')
        f.write('Frames: %s\n' % self.frameCount)
        f.write('Frame Time: %f\n' % self.frameTime)

        allJoints = [joint for joint in self.getJointsBVHOrder() if not joint.isEndConnector()]
        jointsData = [joint.matrixPoses for joint in allJoints]
        nJoints = len(jointsData)
        nFrames = len(jointsData[0])
        totalChannels = sum([len(joint.channels) for joint in allJoints])

        for fIdx in range(self.frameCount):
            frameData = []
            for joint in allJoints:
                offset = fIdx * len(joint.channels)
                frameData.extend(joint.frames[offset:offset + len(joint.channels)])
            frameData = [str(fl) for fl in frameData]
            f.write('%s\n' % " ".join(frameData))
        f.close()

    def _writeJoint(self, f, joint, ident):
        if joint.name == "End effector":
            offset = joint.offset
            f.write('\t' * (ident + 1) + 'End Site\n')
            f.write('\t' * (ident + 1) + '{\n')
            f.write('\t' * (ident + 2) + "OFFSET	%s	%s	%s\n" % (offset[0], offset[1], offset[2]))
            f.write('\t' * (ident + 1) + '}\n')
        else:
            if joint.isRoot():
                f.write('ROOT ' + joint.name + '\n')
                f.write('{\n')
            else:
                f.write('\t' * ident + 'JOINT ' + joint.name + '\n')
                f.write('\t' * ident + '{\n')
            offset = joint.offset
            f.write('\t' * (ident + 1) + "OFFSET	%f  %f  %f\n" % (offset[0], offset[1], offset[2]))
            f.write('\t' * (ident + 1) + 'CHANNELS %s %s\n' % (len(joint.channels), " ".join(joint.channels)))

            for child in joint.children:
                self._writeJoint(f, child, ident + 1)
            f.write('\t' * ident + '}\n')

    def __expectKeyword(self, keyword, fp):
        line = fp.readline()
        words = line.split()
        
        if words[0] != keyword:
            raise RuntimeError('Expected %s found %s' % (keyword, words[0]))

        return words

    def __readJoint(self, joint, fp):
        self.__expectKeyword('{', fp)

        # Calculate position from offset
        words = self.__expectKeyword('OFFSET', fp)
        offset = [float(x) for x in words[1:4]]
        self.__calcPosition(joint, offset)
        
        words = self.__expectKeyword('CHANNELS', fp)
        nChannels = int(words[1])
        joint.channels = words[2:]

        if int(nChannels) != len(joint.channels):
            RuntimeError('Expected %d channels found %d' % (nChannels, len(joint.channels)))
        
        # Read child joints
        parentName = joint.getName()
        while True:
            line = fp.readline()
            words = line.split()
            
            if words[0] == 'JOINT':
                child = self.addJoint(parentName, words[1])
                self.__readJoint(child, fp)
                
            elif words[0] == 'End': # Site
                child = self.addJoint(parentName, 'End effector')
                
                self.__expectKeyword('{', fp)

                # Get OFFSET
                words = self.__expectKeyword('OFFSET', fp)
                offset = [float(x) for x in words[1:4]]
                self.__calcPosition(child, offset)
                
                self.__expectKeyword('}', fp)
                
            elif words[0] == '}':
                break
                
            else:
                raise RuntimeError('Expected %s found %s' % ('JOINT, End Site or }', words[0]))

    def __processChannelData(self, joint, data):
        """
        Distribute animation channel data for one frame or motion sample, 
        loaded from a BVH file, among the joints of the skeleton structure.
        """
        nChannels = len(joint.channels)
        joint.frames.extend(data[:nChannels])
        data = data[nChannels:]

        return data

    def __calcPosition(self, joint, offset):
        """
        Calculate this joint's position using offset (from parent) defined in
        BVH hierarchy data.
        """
        joint.offset = np.asarray(offset, dtype=np.float32)

        if self.convertFromZUp:
            y = joint.offset[1]
            joint.offset[1] = joint.offset[2]
            joint.offset[2] = -y

        # Calculate absolute joint position
        if joint.parent:
            joint.position = np.add(joint.parent.position, joint.offset)
        else:
            joint.position = joint.offset[:]

        # Create relative rest matrix for joint (only translation)
        joint.matRestRelative = np.identity(4, dtype=np.float32)
        joint.matRestRelative[:3,3] = joint.offset

        # Create world rest matrix for joint (only translation)
        joint.matRestGlobal = np.identity(4, dtype=np.float32)
        joint.matRestGlobal[:3,3] = joint.position

    def scale(self, scaleFactor):
        """
        Scale the skeleton stored in this BVH data.
        """
        oldZup = self.convertFromZUp
        self.convertFromZUp = False     # Avoid converting again

        for joint in self.getJoints():
            # Rescale joint offset and recalculate positions and rest matrices
            self.__calcPosition(joint, scaleFactor * joint.offset)
            
            # Rescale translation channels
            nFrames = self.frameCount
            for (chanIdx, channel) in enumerate(joint.channels):
                nChannels = len(joint.channels)
                dataLen = nFrames * nChannels
                if channel in ["Xposition", "Yposition", "Zposition"]:
                    joint.frames[chanIdx:dataLen:nChannels] *= scaleFactor

            # Recalculate pose matrices
            joint.calculateFrames()

        self.convertFromZUp = oldZup


class BVHJoint():

    def __init__(self, name, skel):
        self.name = name
        self.skeleton = skel
        self.children = []
        self.parent = None

        # Rest position data
        self.offset = np.zeros(3,dtype=np.float32)       # Relative offset from parent joint in rest
        self.position = np.zeros(3,dtype=np.float32)     # Absolute position in rest position

        # Animation data
        self.channels = []
        self.frames = []

        # Transformation matrices
        # static
        #  matRestGlobal:     4x4 rest matrix, relative world
        #  matRestRelative:   4x4 rest matrix, relative parent
        # posed
        #  matrixPoses        n list of 4x4 pose matrices for n frames, relative parent and own rest pose
        self.matRestRelative = None
        self.matRestGlobal = None
        self.matrixPoses = None

    # TODO calculatePosition is defined on BVHSkeleton, but this is in BVHJoint, make uniform
    def calculateFrames(self):
        """
        Calculate transformation matrices from this joint's (BVH) channel data.
        """
        self.frames = np.asarray(self.frames, dtype=np.float32)
        nChannels = len(self.channels)
        nFrames = self.skeleton.frameCount
        dataLen = nFrames * nChannels
        if len(self.frames) < dataLen:
            log.debug("Frame data: %s", self.frames)
            raise RuntimeError('Expected frame data length for joint %s is %s found %s' % ( self.getName(),
                dataLen, len(self.frames)))

        rotOrder = ""
        rotAngles = []
        rXs = rYs = rZs = None
        for (chanIdx, channel) in enumerate(self.channels):

            if channel == "Xposition":
                rXs = self.frames[chanIdx:dataLen:nChannels]
            elif channel == "Yposition":
                rYs = self.frames[chanIdx:dataLen:nChannels]
            elif channel == "Zposition":
                rZs = self.frames[chanIdx:dataLen:nChannels]

            elif channel == "Xrotation":
                aXs = D*self.frames[chanIdx:dataLen:nChannels]
                rotOrder = "x" + rotOrder
                rotAngles.append(aXs)
            elif channel == "Yrotation":
                if self.skeleton.convertFromZUp:
                    aYs = -D*self.frames[chanIdx:dataLen:nChannels]
                    rotOrder = "z" + rotOrder
                else:
                    aYs = D*self.frames[chanIdx:dataLen:nChannels]
                    rotOrder = "y" + rotOrder
                rotAngles.append(aYs)
            elif channel == "Zrotation":
                aZs = D*self.frames[chanIdx:dataLen:nChannels]
                if self.skeleton.convertFromZUp:
                    rotOrder = "y" + rotOrder
                else:
                    rotOrder = "z" + rotOrder
                rotAngles.append(aZs)

        rotOrder = "s"+ rotOrder
        self.rotOrder = rotOrder

        # Calculate pose matrix for each animation frame
        self.matrixPoses = animation.emptyTrack(nFrames)

        # Add rotations to pose matrices
        if len(rotAngles) > 0 and len(rotAngles) < 3:
            # TODO allow partial rotation channels too?
            pass
        elif len(rotAngles) >= 3:
            for frameIdx in range(nFrames):
                self.matrixPoses[frameIdx,:3,:3] = tm.euler_matrix(rotAngles[2][frameIdx], rotAngles[1][frameIdx], rotAngles[0][frameIdx], axes=rotOrder)[:3,:3]

            # TODO eliminate loop with numpy?
            '''
            for rotAngle in rotAngles:  
                self.matrixPoses[:] = tm.euler_matrix(rotAngle[2], rotAngle[1], rotAngle[0], axes=rotOrder))
            # unfortunately tm.euler_matrix is not a np ufunc
            '''

        # Add translations to pose matrices
        # Allow partial transformation channels too
        if rXs != None or rYs != None or rZs != None:
            if rXs == None:
                rXs = np.zeros(nFrames, dtype=np.float32)
            if rYs == None:
                rYs = np.zeros(nFrames, dtype=np.float32)
            if rZs == None:
                rZs = np.zeros(nFrames, dtype=np.float32)

            self.matrixPoses[:,:3,3] = np.column_stack([rXs,rYs,rZs])[:,:]

    def addChild(self, joint):
        self.children.append(joint)
        joint.parent = self

    def getName(self):
        return self.name

    def hasParent(self):
        return self.parent != None

    def isRoot(self):
        return not self.hasParent()

    def hasChildren(self):
        return len(self.children) > 0

    def isEndConnector(self):
        return not self.hasChildren()


def load(filename, convertFromZUp = False):
    result = BVH()
    result.convertFromZUp = convertFromZUp
    result.fromFile(filename)
    return result

def createFromSkeleton(skel, animationTrack = None):
    result = BVH()
    result.fromSkeleton(skel, animationTrack)
    return result
