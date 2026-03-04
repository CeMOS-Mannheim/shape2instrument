def writeMIS(self):
    """"
    Export a selected segment/contour to an existing .mis-File (adding an area or region of interest)
    first, a .mis file need to be pre-selected by the function importMIS.
    """
    if self.defaultrasterInput.currentText() == '5 um':
        rasterSize = 5
    if self.defaultrasterInput.currentText() == '10 um':
        rasterSize = 10
    elif self.defaultrasterInput.currentText() == '20 um':
        rasterSize = 20
    elif self.defaultrasterInput.currentText() == '30 um':
        rasterSize = 30
    elif self.defaultrasterInput.currentText() == '40 um':
        rasterSize = 40
    elif self.defaultrasterInput.currentText() == '50 um':
        rasterSize = 50
    elif self.defaultrasterInput.currentText() == '100 um':
        rasterSize = 100

    raster_size = [rasterSize, rasterSize]
    local_reference = [0, 0]
    polygon_type = str(self.defaultpolygontypeMIS.currentText())
    area_name = str(self.defaultareanameInputString + '_')
    #

    newMis = mismaker(self.fileNameMis, defaultraster=raster_size,
                      defaultlocalreference=local_reference,
                      defaultpolygontype=polygon_type, defaultareaname=area_name)
    #
    newMis.load_mis(self.fileNameMis, mode="add")

    #
    yInvert = int(shape(self.image_optical)[1])
    shapes = []
    # add Infrared
    try:
        print('Infrared')
        column = 0
        for i in range(len(self.ListRegionsInfrared)):
            key = list(self.ListRegionsInfrared.keys())
            jj = 0
            print('Infrared_1')
            for region in self.ListRegionsInfrared[key[i]]:
                print('Infrared_2')
                if self.InfraredTreeElements[i].checkState(column) == QtCore.Qt.Checked:
                    print('Infrared_3')
                    jj = jj + 1

                    x = []
                    y = []

                    pathNew = region.path()
                    numberOfPoints = int(pathNew.elementCount())
                    print("numberOfPoints: ", numberOfPoints)
                    polygonList = zeros((numberOfPoints, 2))
                    for ii in range(numberOfPoints):
                        point = QtCore.QPointF(pathNew.elementAt(ii))
                        # print(str(i), '-Element: x', round(point.x()), 'y: ', round(point.y()))
                        x = append(x, int(point.x()))
                        y = append(y, int(point.y()))
                    polygonList[:, 0] = x[:]
                    polygonList[:, 1] = y[:]
                    print(polygonList)
                    shapes.append(polygonList)
    except:
        pass

    # add shapes
    try:
        column = 0
        for i in range(len(self.ListRegionsShapes)):
            key = list(self.ListRegionsShapes.keys())
            jj = 0
            for region in self.ListRegionsShapes[key[i]]:
                if self.ShapesTreeElements[i].checkState(column) == QtCore.Qt.Checked:
                    jj = jj + 1

                    x = []
                    y = []

                    # obtain possible translation
                    try:
                        x0 = region.pos().x()
                        y0 = region.pos().y()
                    except:
                        pass

                    pathNew = region.path()
                    numberOfPoints = int(pathNew.elementCount())
                    print("numberOfPoints: ", numberOfPoints)
                    polygonList = zeros((numberOfPoints, 2))
                    for ii in range(numberOfPoints):
                        point = QtCore.QPointF(pathNew.elementAt(ii))
                        # print(str(i), '-Element: x', round(point.x()), 'y: ', round(point.y()))
                        x = append(x, int(point.x() + x0))
                        y = append(y, int(point.y() + y0))
                    polygonList[:, 0] = x[:]
                    polygonList[:, 1] = y[:]
                    shapes.append(polygonList)
    except:
        pass

    contourDict = {}
    i = 0
    for contour in shapes:
        contourHelp = (contour + 0.0)
        contourHelp[:, 0] = (around(contourHelp[:, 0])) + int(self.OffsetXInputValue)
        contourHelp[:, 1] = yInvert - (around(contourHelp[:, 1])) + int(self.OffsetYInputValue)
        contourDict[i] = {"contour": contourHelp.astype(int)}
        i = i + 1

    newMis.add_contours(contourDict)
    newMis.save_mis(self.fileNameMis)