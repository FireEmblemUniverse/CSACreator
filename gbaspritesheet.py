from gbaimage import GBAImage
from tilemap import TileMap

class GBASpriteSheet(object):
  """docstring for GBASpriteSheet"""
  def __init__(self, palette, width, height):
    super(GBASpriteSheet, self).__init__()
    self.image = GBAImage.blankImage(palette,width,height)
    self.map = TileMap.blankTileMap(width,height)

  def findInsertionLocation(self,sprite):
    rows = sprite.height #4
    columns = sprite.width #4
    max_row = self.image.height - rows #4-4 = 0 (this is the only option)
    max_col = self.image.width - columns #

    # todo: implement match checking for if the sprite is already there
    for row in range(max_row+1):
      for col in range(max_col+1):
        if self.map.allMarkedAs(col,row,columns,rows,False):
          return (col, row)
    #if it can't fit on this sheet
    return None

  def blit(self, src, to_x, to_y):
    self.image.blit(src,to_x,to_y,False)
    self.map.setMarks(to_x,to_y,src.width,src.height,True)

  def usedTileAt(self, x, y):
    return self.map.allMarkedAs(x,y,1,1,True)

if __name__ == '__main__':
  g = GBAImage("1.png")
  ss = GBASpriteSheet(g.palette, 32, 4)
  print(ss.map)