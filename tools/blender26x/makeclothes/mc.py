# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# Project Name:        MakeHuman
# Product Home Page:   http://www.makehuman.org/
# Code Home Page:      http://code.google.com/p/makehuman/
# Authors:             Thomas Larsson
# Script copyright (C) MakeHuman Team 2001-2013
# Coding Standards:    See http://www.makehuman.org/node/165

from maketarget import mh

class CSettings(mh.CSettings):

    def __init__(self, version):
        mh.CSettings.__init__(self, version)

        if version == "alpha7":
            self.topOfSkirt    = list(range(16691,16707))

            self.bodyPartVerts = {
                "Body" : ((13868, 14308), (881, 13137), (10854, 10981)),
                "Head" : ((4302, 8697), (8208, 8220), (8223, 6827)),
                "Torso" : ((3464, 10305), (6930, 7245), (14022, 14040)),
                "Arm" : ((14058, 14158), (4550, 4555), (4543, 4544)),
                "Hand" : ((14058, 15248), (3214, 3264), (4629, 5836)),
                "Leg" : ((3936, 3972), (3840, 3957), (14165, 14175)),
                "Foot" : ((4909, 4943), (5728, 12226), (4684, 5732)),
                "Eye" : ((142, 197), (76, 141), (169, 225)),
            }

        elif version == "hm08":

            self.topOfSkirt = [
                15773, 16033, 16034, 16035, 16036, 16037, 16038, 16039, 16040, 16042, 16047, 16048,
                16049, 16050, 16056, 16510, 16528, 17090, 17347, 17360, 17361, 17362, 17363, 17364,
                17365, 17366, 17367, 17369, 17374, 17375, 17376, 17377, 17378, 17384, 17844, 17862,
            ]

            self.bodyPartVerts = {
                "Body" : ((13868, 14308), (10854, 10981), (881, 13137)),
                "Head" : ((5399, 11998), (962, 5320),  (791,881)),
                "Torso" : ((3924, 10589), (1892, 3946), (1524, 4370)),
                "Arm" : ((8300, 10210), (10076, 10543), (10064, 10069)),
                "Hand" : ((8938, 10548), (9864, 10267), (9881, 10318)),
                "Leg" : ((11133, 11141), (11130, 11135), (11025, 11460)),
                "Foot" : ((12839, 12860), (11609, 12442), (12828, 12888)),
                "Eye" : ((14618, 14645), (14650, 14658), (14636, 14663)),
            }


settings = {
    "alpha7" : CSettings("alpha7"),
    "hm08"   : CSettings("hm08"),
    "None"   : None
}


#
#   goodName(name):
#   getFileName(pob, context, ext):
#

def goodName(name):
    newName = name.replace('-','_').replace(' ','_')
    return newName.lower()


def getFileName(pob, folder, ext):
    import os
    name = goodName(pob.name)
    outdir = '%s/%s' % (folder, name)
    outdir = os.path.realpath(os.path.expanduser(outdir))
    if not os.path.exists(outdir):
        print(("Creating directory %s" % outdir))
        os.makedirs(outdir)
    outfile = os.path.join(outdir, "%s.%s" % (name, ext))
    return (outdir, outfile)
