#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Glynn Clements

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

TODO
"""

import numpy as np
import image_qt

class Image(object):
    def __init__(self, path = None, width = 0, height = 0, bitsPerPixel = 32, components = None, data = None):
        if path is not None:
            if isinstance(path, Image):
                # Create a copy of the image.
                self._data = path.data.copy()
            elif isinstance(path, image_qt.QtGui.QPixmap):
                qimg = path.toImage()
                self._data = image_qt.load(qimg)
            else:   # Path string / QImage.
                self._data = image_qt.load(path)
        elif data is not None:
            if isinstance(data, Image):
                # Share data between images.
                self._data = data.data
            elif isinstance(data, str):
                self._data = image_qt.load(data)
            else:   # Data array.
                self._data = data
        else:
            if components is None:
                if bitsPerPixel == 32:
                    components = 4
                elif bitsPerPixel == 24:
                    components = 3
                else:
                    raise NotImplementedError("bitsPerPixel must be 24 or 32")
            self._data = np.empty((height, width, components), dtype=np.uint8)
        self._data = np.ascontiguousarray(self._data)

    @property
    def size(self):
        h, w, c = self._data.shape
        return (w, h)

    @property
    def width(self):
        h, w, c = self._data.shape
        return w

    @property
    def height(self):
        h, w, c = self._data.shape
        return h

    @property
    def components(self):
        h, w, c = self._data.shape
        return c

    @property
    def bitsPerPixel(self):
        h, w, c = self._data.shape
        return c * 8

    @property
    def data(self):
        return self._data

    def save(self, path):
        image_qt.save(path, self._data)

    def toQImage(self):
        if self.components == 3:
            fmt = image_qt.QtGui.QImage.Format_RGB888
        else:
            fmt = image_qt.QtGui.QImage.Format_ARGB32
        return image_qt.QtGui.QImage(self.data.tostring(), self.data.shape[0], self.data.shape[1], fmt)

    def resized_(self, width, height):
        dw, dh = width, height
        sw, sh = self.size
        xmap = np.floor((np.arange(dw) + 0.5) * sw / dw).astype(int)
        ymap = np.floor((np.arange(dh) + 0.5) * sh / dh).astype(int)
        return self._data[ymap,:][:,xmap]

    def resized(self, width, height):
        return Image(data = self.resized_(width, height))

    def resize(self, width, height):
        self._data = self.resized_(width, height)

    def blit(self, other, x, y):
        dh, dw, dc = self._data.shape
        sh, sw, sc = other._data.shape
        if sc != dc:
            raise ValueError("source image has incorrect format")
        sw = min(sw, dw - x)
        sh = min(sh, dh - y)
        self._data[y:y+sh,x:x+sw,:] = other._data

    def flip_vertical(self):
        return Image(data = self._data[::-1,:,:])

    def flip_horizontal(self):
        return Image(data = self._data[:,::-1,:])

    def __getitem__(self, xy):
        if not isinstance(xy, tuple) or len(xy) != 2:
            raise TypeError("tuple of length 2 expected")

        x, y = xy

        if not isinstance(x, int) or not isinstance(y, int):
            raise TypeError("tuple of 2 ints expected")

        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            raise IndexError("element index out of range")

        pix = self._data[y,x,:]
        if self.components == 4:
            return (pix[0], pix[1], pix[2], pix[3])
        elif self.components == 3:
            return (pix[0], pix[1], pix[2], 255)
        elif self.components == 2:
            return (pix[0], pix[0], pix[0], pix[1])
        elif self.components == 1:
            return (pix[0], pix[0], pix[0], 255)
        else:
            return None

    def __setitem__(self, xy, color):
        if not isinstance(xy, tuple) or len(xy) != 2:
            raise TypeError("tuple of length 2 expected")

        x, y = xy

        if not isinstance(x, int) or not isinstance(y, int):
            raise TypeError("tuple of 2 ints expected")

        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            raise IndexError("element index out of range")

        if not isinstance(color, tuple):
            raise TypeError("tuple expected")

        self._data[y,x,:] = color

    def convert(self, components):
        if self.components == components:
            return self

        hasAlpha = self.components in (2,4)
        needAlpha = components in (2,4)

        if hasAlpha:
            alpha = self._data[...,-1]
            color = self._data[...,:-1]
        else:
            alpha = None
            color = self._data

        isMono = self.components in (1,2)
        toMono = components in (1,2)

        if isMono and not toMono:
            color = np.dstack((color, color, color))
        elif toMono and not isMono:
            color = np.sum(color.astype(np.uint16), axis=-1) / 3
            color = color.astype(np.uint8)[...,None]

        if needAlpha and alpha is None:
            alpha = np.zeros_like(color[...,:1]) + 255

        if needAlpha:
            data = np.dstack((color, alpha))
        else:
            data = color

        return type(self)(data = data)
