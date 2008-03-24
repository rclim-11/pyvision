# PyVision License
#
# Copyright (c) 2006-2008 David S. Bolme
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
# 
# 3. Neither name of copyright holders nor the names of its contributors
# may be used to endorse or promote products derived from this software
# without specific prior written permission.
# 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import unittest
import os.path
import math

from PIL.Image import AFFINE,NEAREST,BILINEAR,BICUBIC
from numpy import array,dot
from numpy.linalg import inv,solve

import pyvision
from pyvision.types.Image import Image, TYPE_PIL, TYPE_MATRIX2D
from pyvision.types.Point import Point
from pyvision.types.Rect import Rect

def AffineTranslate(dx,dy,new_size,filter=BILINEAR):
    ''' Construct an affine tranfrom that performs a translation. '''
    matrix = array([[1,0,dx],[0,1,dy],[0,0,1]],'d')

    return AffineTransform(matrix,new_size,filter)
    
def AffineScale(scale,new_size,filter=BILINEAR):
    ''' Construct an affine tranfrom that performs a scale. '''
    matrix = array([[scale,0,0],[0,scale,0],[0,0,1]],'d')

    return AffineTransform(matrix,new_size,filter)
    
def AffineRotate(theta,new_size,filter=BILINEAR):
    ''' Construct an affine tranfrom that performs a rotation. Theta is radians clockwise'''
    matrix = array([[math.cos(theta),-math.sin(theta),0],[math.sin(theta),math.cos(theta),0],[0,0,1]],'d')

    return AffineTransform(matrix,new_size,filter)
    
def AffineFromRect(rect,new_size,filter=BILINEAR):
    ''' An affine transform that crops out a rectangle and returns it as an image. '''
    w,h = new_size
    
    x_scale = float(w)/rect.w
    y_scale = float(h)/rect.h
    x_trans = -rect.x*x_scale
    y_trans = -rect.y*y_scale
    matrix = array([[x_scale,0,x_trans],[0,y_scale,y_trans],[0,0,1]],'d')

    return AffineTransform(matrix,new_size,filter)
    
def AffineFromPoints(src1,src2,dst1,dst2,new_size,filter=BILINEAR):
    ''' 
    An affine transform that will rotate, translate, and scale to map one 
    set of points to the other. Used to align eye coordinates in face images.
    
    Find a transform (a,b,tx,ty) such that it maps the source points to the 
    destination points:
    a*x1-b*y1+tx = x2
    b*x1+a*y1+ty = y2
    
    The mapping between the two points creates a set of  four linear equations 
    with four unknowns.
    '''
    
    # Compute the transformation parameters
    A = [[src1.X(),-src1.Y(),1,0],
         [src1.Y(),src1.X(),0,1],
         [src2.X(),-src2.Y(),1,0],
         [src2.Y(),src2.X(),0,1]]
    b = [dst1.X(),dst1.Y(),dst2.X(),dst2.Y()]
    A = array(A)
    b = array(b)
    result = solve(A,b)
    
    a,b,tx,ty = result    
    # Create the transform matrix
    matrix = array([[a,-b,tx],[b,a,ty],[0,0,1]],'d')
    
    return AffineTransform(matrix,new_size,filter)

    
# TODO: add least squares factories

class AffineTransform:
    ''' Perform a transform one image to another. '''
    def __init__(self,matrix,new_size,filter=BILINEAR):
        self.matrix = matrix
        self.inverse = inv(matrix)
        self.size = new_size
        self.filter = filter
    
    def transformImage(self,im):
        ''' Transform an image. '''
        matrix = self.inverse
        if im.getType() == TYPE_PIL:
            data = (matrix[0,0],matrix[0,1],matrix[0,2],matrix[1,0],matrix[1,1],matrix[1,2])
            pil = im.asPIL().transform(self.size, AFFINE, data, self.filter)
            return Image(pil)
        else:
            raise NotImplementedError("Unhandled image type for affine transform.")
        
    def transformPoint(self,pt):
        ''' Transform a point from the old image to the new image '''
        vec = dot(self.matrix,pt.asVector2H())
        return Point(x=vec[0,0],y=vec[1,0],w=vec[2,0])
        
    def invertPoint(self,pt):
        ''' Transform a point from the old image to the new image '''
        vec = dot(self.inverse,pt.asVector2H())
        return Point(x=vec[0,0],y=vec[1,0],w=vec[2,0])
        
    def asMatrix(self):
        ''' Return the transform as a 3 by 3 matrix '''
        return self.matrix
    
    def __mul__(self,affine):
        return AffineTransform(dot(self.matrix,affine.matrix),self.size,self.filter)


# TODO: Add unit tests
class _AffineTest(unittest.TestCase):
    
    def setUp(self):
        fname = os.path.join(pyvision.__path__[0],'data','nonface','NONFACE_13.jpg')
        self.test_image = Image(fname)
        #self.test_image.show()
    
    def test_rotation(self):
        transform = AffineRotate(3.14/8,(640,480))
        im = transform.transformImage(self.test_image)
        # im.show()
        
        pt = transform.transformPoint(Point(320,240))
        self.assertAlmostEqual(pt.X(),203.86594448424472)
        self.assertAlmostEqual(pt.Y(),344.14920700118842)

        pt = transform.invertPoint(Point(320,240))
        self.assertAlmostEqual(pt.X(),387.46570317672939)
        self.assertAlmostEqual(pt.Y(),99.349528744542198)
        
    def test_scale(self):
        transform = AffineScale(1.5,(640,480))
        im = transform.transformImage(self.test_image)
        #im.show()
        
        pt = transform.transformPoint(Point(320,240))
        self.assertAlmostEqual(pt.X(),480.)
        self.assertAlmostEqual(pt.Y(),360.)

        pt = transform.invertPoint(Point(320,240))
        self.assertAlmostEqual(pt.X(),213.33333333333331)
        self.assertAlmostEqual(pt.Y(),160.)
        
    def test_translate(self):
        transform = AffineTranslate(10.,15.,(640,480))
        im = transform.transformImage(self.test_image)
        #im.show()
        
        pt = transform.transformPoint(Point(320,240))
        self.assertAlmostEqual(pt.X(),330.)
        self.assertAlmostEqual(pt.Y(),255.)

        pt = transform.invertPoint(Point(320,240))
        self.assertAlmostEqual(pt.X(),310.)
        self.assertAlmostEqual(pt.Y(),225.)
        
    def test_from_rect(self):
        
        self.assert_(False) # Fix this test
        
        transform = AffineTranslate(10.,15.,(640,480))
        im = transform.transformImage(self.test_image)
        #im.show()
        
        pt = transform.transformPoint(Point(320,240))
        self.assertAlmostEqual(pt.X(),330.)
        self.assertAlmostEqual(pt.Y(),255.)

        pt = transform.invertPoint(Point(320,240))
        self.assertAlmostEqual(pt.X(),310.)
        self.assertAlmostEqual(pt.Y(),225.)
        
    def test_from_points(self):
        
        self.assert_(False) # Fix this test
        
        transform = AffineTranslate(10.,15.,(640,480))
        im = transform.transformImage(self.test_image)
        #im.show()
        
        pt = transform.transformPoint(Point(320,240))
        self.assertAlmostEqual(pt.X(),330.)
        self.assertAlmostEqual(pt.Y(),255.)

        pt = transform.invertPoint(Point(320,240))
        self.assertAlmostEqual(pt.X(),310.)
        self.assertAlmostEqual(pt.Y(),225.)
        
    def test_sim_least_sqr(self):
        
        self.assert_(False) # Fix this test
        
        transform = AffineTranslate(10.,15.,(640,480))
        im = transform.transformImage(self.test_image)
        #im.show()
        
        pt = transform.transformPoint(Point(320,240))
        self.assertAlmostEqual(pt.X(),330.)
        self.assertAlmostEqual(pt.Y(),255.)

        pt = transform.invertPoint(Point(320,240))
        self.assertAlmostEqual(pt.X(),310.)
        self.assertAlmostEqual(pt.Y(),225.)
        
    def test_affine_least_sqr(self):
        
        self.assert_(False) # Fix this test
        
        transform = AffineTranslate(10.,15.,(640,480))
        im = transform.transformImage(self.test_image)
        #im.show()
        
        pt = transform.transformPoint(Point(320,240))
        self.assertAlmostEqual(pt.X(),330.)
        self.assertAlmostEqual(pt.Y(),255.)

        pt = transform.invertPoint(Point(320,240))
        self.assertAlmostEqual(pt.X(),310.)
        self.assertAlmostEqual(pt.Y(),225.)

    def test_affine_mul(self):
        
        self.assert_(False) # Fix this test
        
        transform = AffineTranslate(10.,15.,(640,480))
        im = transform.transformImage(self.test_image)
        #im.show()
        
        pt = transform.transformPoint(Point(320,240))
        self.assertAlmostEqual(pt.X(),330.)
        self.assertAlmostEqual(pt.Y(),255.)

        pt = transform.invertPoint(Point(320,240))
        self.assertAlmostEqual(pt.X(),310.)
        self.assertAlmostEqual(pt.Y(),225.)
        
    