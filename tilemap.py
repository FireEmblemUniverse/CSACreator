class TileMap(object):
    def __init__(self, source=None):
        if source:
            width = source.getTileWidth()
            height = source.getTileHeight()
            self._map = [[(not source.blankTileAt(x, y)) for x in range(width)] for y in range(height)]
            self._markCount = 0
            for x in self._map:
                for y in x:
                    if y == True:
                        self._markCount += 1

    @classmethod
    def blankTileMap(self, width, height):
        result = TileMap()
        result._map = [[False for x in range(width)] for y in range(height)]
        result._markCount = 0
        return result

    def getCount(self):
        return self._markCount

    def allMarkedAs(self, c, r, cs, rs, mark): #this one may cause problems....
        maxcol = c+cs #2+1 = 3
        maxrow = r+rs #0+4 = 4
        for row in range(r,maxrow): #row 0 to row 4
            for col in range(c,maxcol): #column 2 to column 2
                if self._map[row][col] != mark:
                    return False
        return True

    def setMarks(self, c,r,cs,rs,mark):
        maxcol = c+cs #2+1 = 3
        maxrow = r+rs #0+4 = 4
        for row in range(r,maxrow):
            for col in range(c,maxcol):
                if (self._map[row][col] and (not mark)):
                    self._markCount -= 1
                elif ((not self._map[row][col]) and mark):
                    self._markCount += 1
                self._map[row][col] = mark

    def extractMarkedRegion(self, columns, rows):
        if ((columns*rows)>self._markCount):
            return None
        max_row = len(self._map) - rows +1
        max_col = len(self._map[0]) - columns +1

        for row in range(max_row):
            for column in range(max_col):
                if self.allMarkedAs(column,row,columns,rows,True):
                    self.setMarks(column,row,columns,rows,False)
                    return [column, row, columns, rows]
        return None


if __name__ == '__main__':
    a = TileMap.blankTileMap(32,4)
    print(a.allMarkedAs(2,0,1,4,False))