from PIL import Image
import numpy as np

class Palette(object):
  """is a palette for a thing."""
  def __init__(self, arg):
    super(Palette, self).__init__()
    self.arg = arg

  def condense(colour):
    r = colour[0]>>3
    g = colour[1]>>3
    b = colour[2]>>3
    return (b<<10)|(g<<5)|r
    
class GBAImage(object):
  """Format of GBA graphics:
8x8 tiles with 32 bytes per tile; each nibble of each byte is a single pixel

Gonna assume it's already indexed colour png.

Nibbles are reversed for each byte; bytes are in order
So if the top left tile of an image has something like 10 32 54 76
and the tile to the right of it begins with 98 BA DC FE
then the first 16 pixels along the top row will count 0-F"""

  def __init__(self, infile=None):
    super(GBAImage, self).__init__()
    if infile:
      self.infile = infile # infile is an indexed colour PNG.
      self.process(infile)

  @classmethod
  def blankImage(self, palette, width, height):
    result = GBAImage()
    result.palette = palette
    result.width = width
    result.pxwidth = width*8
    result.height = height
    result.pxheight = height*8
    result.pixels = np.zeros((height, width))
    result.image = bytes(width*height*32)
    return result

  @classmethod
  def imageFromSlice(self, src, x, y, width, height):
    """creates a new image from a slice of the old"""
    result = GBAImage()
    result.palette = src.palette
    result.width = width
    result.height = height
    result.pxwidth = width*8
    result.pxheight = height*8
    result.pixels = src.pixels[y*8:y*8+result.pxheight,x*8:x*8+result.pxwidth]
    result.image = result.binify(result.pixels)
    return result

  def process(self,infile):
    im = Image.open(infile)
    pal = im.getpalette()
    self.pxwidth, self.pxheight = im.size
    self.width = self.pxwidth>>3
    self.height = self.pxheight>>3
    if pal == None:
      im = im.quantize(colors=16) # convert from rgb
      pal = im.getpalette()
    palette = list(chunks(pal,3)) # stored as [r,g,b]
    gbapal = [Palette.condense(colour) for colour in palette[:16]]
    self.palette = gbapal
    self.pixels = np.array(im)
    self.image = self.binify(self.pixels)

  def binify(self, pixels):
    """stored as 8x8 tiles"""
    rows = np.vsplit(pixels, self.height)
    tiles = []
    for row in rows:
      tiles.append(np.hsplit(row,self.width))
    l= [item for sublist in tiles for item in sublist]
    a = [item for sublist in l for item in sublist]
    b = [item for sublist in a for item in sublist]
    result = b''
    #reduced it to a 1d list
    for x, y in zip(*[iter(b)]*2):
      result += int(x+(y<<4)).to_bytes(1,'little')
    return result
    
  def getTileWidth(self):
    return self.width

  def getTileHeight(self):
    return self.height

  def blankTileAt(self,x,y):
    index = ((y*self.width)+x) * 32
    return (self.image[index:index+32] == bytes(32))

  def blit(self, src, to_x, to_y, transparent=False):
    for i in range(src.width):
      for j in range(src.height):
        offset = (j*src.width+i)*32
        tiledata = src.image[offset:offset+32]
        dest = (to_y+j)*self.width*32+(to_x+i)*32
        imgbuffer = bytearray(self.image)
        imgbuffer[dest:dest+32] = tiledata
        self.image = bytes(imgbuffer)

def getTopRight(path):
  im = Image.open(path)
  px = im.load()
  cl = px[im.width-1,0] #top right pixel
  if type(cl) is int:
    if cl == 0: # if the top right pixel is colour 0 then great
      return None
    else: #if it's not, assume the transparent colour is 0
      return '0'
  else:
    # hx = "#{0:02x}{1:02x}{2:02x}".format(cl[0], cl[1], cl[2])
    cl_r = cl[0]>>3
    cl_g = cl[1]>>3
    cl_b = cl[2]>>3
    hx = "{0:04}".format(cl_r|(cl_g<<5)|(cl_b<<10))
    return hx

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

if __name__ == '__main__':
  print(getTopRight('test.png'))