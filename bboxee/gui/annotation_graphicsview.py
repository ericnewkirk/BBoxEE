# -*- coding: utf-8 -*-
#
# Bounding Box Editor and Exporter (BBoxEE)
# Author: Peter Ersts (ersts@amnh.org)
#
# --------------------------------------------------------------------------
#
# This file is part of Animal Detection Network's (Andenet)
# Bounding Box Editor and Exporter (BBoxEE)
#
# BBoxEE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BBoxEE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.
#
# --------------------------------------------------------------------------
from PyQt5 import QtWidgets, QtCore, QtGui
from enum import Enum


# where in the bbox?
class BBoxRegion(Enum):
    Top = 0
    Bottom = 1
    Left = 2
    Right = 3
    Top_Left = 4
    Top_Right = 5
    Bottom_Left = 6
    Bottom_Right = 7
    Center = 8


class Mode(Enum):
    Move = 0
    Resize = 1
    Create = 3
    Delete = 4


# distance from edge at which to turn on resizing
EDGE_WIDTH = 8
# minimum size side for creation of a new box, drags smaller
# than this in either dimension will be interpreted as clicks
MIN_BOX_SIZE = 3

# width of line forming bounding box
BOX_LINE_WIDTH = 1

# Hover: select a box
# Click+Drag on box: move box
# Click+Drag on an edge or corner: resize a box
# Click+Drag on image: create a new box
# Shift+Click+Drag or Right Click+Drag on image: pan the image
# Click inside box: make sticky
# Click background: unsticky
# Middle Click inside box: delete box
# Arrows: move selected box
# Shift+Arrows: resize selected box

# Control+Click+Drag: create a new box, even inside an existing box

class AnnotationGraphicsView(QtWidgets.QGraphicsView):
    """Custom QGraphicsView for creating and editing annotation
    bounding boxes."""

    created = QtCore.pyqtSignal(QtCore.QRectF)
    resized = QtCore.pyqtSignal(QtCore.QRectF)
    moved = QtCore.pyqtSignal(QtCore.QRectF)
    select_bbox = QtCore.pyqtSignal(QtCore.QPointF)
    delete_event = QtCore.pyqtSignal()
    zoom_event = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        """Class init function."""
        QtWidgets.QGraphicsView.__init__(self, parent)
        self.mode = None
        self.selected_bbox = None
        self.sticky_bbox = False
        self.visible = True

        # what part of the selected bbox are we in?
        self.region = None

        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)

        self.img_size = (0, 0) # width, height
        self.bboxes = []
        self.graphics_scene = QtWidgets.QGraphicsScene()
        self.setScene(self.graphics_scene)
        # enable mouse move events when not dragging
        self.setMouseTracking(True)

    @staticmethod
    def _get_region_and_cursor(point, rect, edge_width):
        """Are we on an edge or corner of a bounding box? Return the right cursor and Region enum."""

        # https://doc.qt.io/qt-5/qt.html#CursorShape-enum
        cursor = QtCore.Qt.OpenHandCursor
        region = BBoxRegion.Center

        # is it near an edge?
        if(point.y() - edge_width < rect.top()):
            # top
            if(point.x() - edge_width < rect.left()):
                # top left
                cursor = QtCore.Qt.SizeFDiagCursor
                region = BBoxRegion.Top_Left
            elif(point.x() + edge_width > rect.right()):
                # top right
                cursor = QtCore.Qt.SizeBDiagCursor
                region = BBoxRegion.Top_Right
            else:
                # just top
                cursor = QtCore.Qt.SizeVerCursor
                region = BBoxRegion.Top
        elif(point.y() + edge_width > rect.bottom()):
            # bottom
            if(point.x() - edge_width < rect.left()):
                # bottom left
                cursor = QtCore.Qt.SizeBDiagCursor
                region = BBoxRegion.Bottom_Left
            elif(point.x() + edge_width > rect.right()):
                # bottom right
                cursor = QtCore.Qt.SizeFDiagCursor
                region = BBoxRegion.Bottom_Right
            else:
                # just bottom
                cursor = QtCore.Qt.SizeVerCursor
                region = BBoxRegion.Bottom
        elif(point.x() - edge_width < rect.left()):
            # left or right
            cursor = QtCore.Qt.SizeHorCursor
            region = BBoxRegion.Left
        elif(point.x() + edge_width > rect.right()):
            cursor = QtCore.Qt.SizeHorCursor
            region = BBoxRegion.Right

        return region, cursor

    @staticmethod
    def move_label(bbox, dx, dy):

        for graphic in bbox.childItems():
            if type(graphic) == QtWidgets.QGraphicsRectItem:
                graphic.moveBy(dx, dy)

    def mouseMoveEvent(self, event):

        point = self.mapToScene(event.pos())

        # are we inside the currently selected box?
        bbox = self.selected_bbox
        if(bbox is None):
            # nothing selected, see if cursor is inside any box
            # select box when hovering over it
            for graphic in self.scene().items():
                if type(graphic) == QtWidgets.QGraphicsRectItem and graphic.sceneBoundingRect().contains(point):

                    # this activates select_bbox in annotation_widget
                    self.select_bbox.emit(point)

                    break

        elif (self.mode == Mode.Move):
            # box is selected and Move mode is active
            dx, dy = point.x() - self.mouse_down.x(), point.y() - self.mouse_down.y()
            bbox.moveBy(dx, dy)
            self.mouse_down = point

        elif(self.mode == Mode.Resize):
            # box is selected and Resize mode is active
            rect = bbox.rect()

            # delta method allows more precise control (doesn't snap to cursor on first move)
            dx, dy = point.x() - self.mouse_down.x(), point.y() - self.mouse_down.y()

            if(self.region == BBoxRegion.Left):
                rect.setLeft(rect.left() + dx)
                AnnotationGraphicsView.move_label(bbox, dx, 0)
            elif(self.region == BBoxRegion.Right):
                rect.setRight(rect.right() + dx)
            elif(self.region == BBoxRegion.Top):
                rect.setTop(rect.top() + dy)
                AnnotationGraphicsView.move_label(bbox, 0, dy)
            elif(self.region == BBoxRegion.Bottom):
                rect.setBottom(rect.bottom() + dy)
            elif(self.region == BBoxRegion.Top_Left):
                new_point = QtCore.QPointF(rect.left() + dx, rect.top() + dy)
                rect.setTopLeft(new_point)
                AnnotationGraphicsView.move_label(bbox, dx, dy)
            elif(self.region == BBoxRegion.Top_Right):
                new_point = QtCore.QPointF(rect.right() + dx, rect.top() + dy)
                rect.setTopRight(new_point)
                AnnotationGraphicsView.move_label(bbox, 0, dy)
            elif(self.region == BBoxRegion.Bottom_Left):
                new_point = QtCore.QPointF(rect.left() + dx, rect.bottom() + dy)
                rect.setBottomLeft(new_point)
                AnnotationGraphicsView.move_label(bbox, dx, 0)
            elif(self.region == BBoxRegion.Bottom_Right):
                new_point = QtCore.QPointF(rect.right() + dx, rect.bottom() + dy)
                rect.setBottomRight(new_point)

            # limit to image interior
            bbox.setRect(rect)

            self.mouse_down = point
        elif(self.mode == Mode.Create):

            rect = QtWidgets.QGraphicsLineItem(self.mouse_down.x(), self.mouse_down.y(), point.x(), point.y()).boundingRect()
            AnnotationGraphicsView.inverseRectTransform(bbox, rect)

            bbox.setRect(rect)
        elif(bbox.sceneBoundingRect().contains(point)):
            # selected box contains cursor
            # just update the region and cursor
            rect = bbox.sceneBoundingRect()

            region, cursor = AnnotationGraphicsView._get_region_and_cursor(point, rect, EDGE_WIDTH)

            self.region = region
            # change cursor for edges and corners
            self.selected_bbox.setCursor(cursor)
        else:
            # selected bbox does not contain cursor, so unselect
            if(not self.sticky_bbox):
                self.region = None
                self.select_bbox.emit(point)

        QtWidgets.QGraphicsView.mouseMoveEvent(self, event)

    def mousePressEvent(self, event):
        """Overload of the mousePressEvent that stores mouse click positions in a list."""

        button = event.button()
        # redirect middle click to shift click
        if button == QtCore.Qt.MiddleButton:
            # delete
            self.mode = Mode.Delete
        elif button == QtCore.Qt.RightButton:
            # manufacture a shift+click event
            handmade_event = QtGui.QMouseEvent(
                QtCore.QEvent.MouseButtonPress, QtCore.QPointF(event.pos()),
                QtCore.Qt.LeftButton, event.buttons(), QtCore.Qt.ShiftModifier)

            self.mousePressEvent(handmade_event)

        elif button == QtCore.Qt.LeftButton and event.modifiers() == QtCore.Qt.ShiftModifier:# QtCore.Qt.NoModifier
            # pan the background image

            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            QtWidgets.QGraphicsView.mousePressEvent(self, event)
        elif button == QtCore.Qt.LeftButton:
            point = self.mapToScene(event.pos())

            bbox = self.selected_bbox
            # are we inside the currently selected box?
            if (bbox is not None and bbox.sceneBoundingRect().contains(point)):
                # yes, initiate move or resize

                # move or resize
                if(self.region == BBoxRegion.Center):
                    # move
                    self.mode = Mode.Move
                    self.mouse_down = point
                    self.selected_bbox.setCursor(QtCore.Qt.ClosedHandCursor)
                else:
                    # resize
                    self.mode = Mode.Resize
                    self.mouse_down = point
            elif(self.sticky_bbox):
                self.region = None
                self.sticky_bbox = False
                # are we inside another box?
                for graphic in self.scene().items():
                    if type(graphic) == QtWidgets.QGraphicsRectItem and graphic.sceneBoundingRect().contains(point):

                        self.sticky_bbox = True

                        break

                # this activates select_bbox in annotation_widget
                self.select_bbox.emit(point)

            else:

                # not inside the selected box, initiate create (new box)
                self.mode = Mode.Create
                self.mouse_down = point
                rect = QtCore.QRectF(point, point)

                new_bbox = self.add_bbox(rect, None, QtCore.Qt.green)
                self.selected_bbox = new_bbox


    @staticmethod
    def sceneRectTransform(bbox):
        """Map the rectanble for a bounding box from item coordinates to scene coordinates.
        Like sceneBoundingBox, except without the extra pixel width line"""
        rect = bbox.rect()
        transform = bbox.sceneTransform()
        return QtCore.QRectF(transform.map(rect.topLeft()), transform.map(rect.bottomRight()))

    @staticmethod
    def inverseRectTransform(bbox, rect):
        """Map the rectangle for a bounding box from scene coordinates to item coordinates."""
        inverted, ok = bbox.sceneTransform().inverted()
        return QtCore.QRectF(inverted.map(rect.topLeft()), inverted.map(rect.bottomRight()))


    def mouseReleaseEvent(self, event):
        """Overload of the MouseReleaseEvent that handles finalization for
        Move, Resize and Create"""
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        point = self.mapToScene(event.pos())

        bbox = self.selected_bbox
        if(bbox is None):
            pass
        elif(self.mode == Mode.Move):
            self.mode = None
            if(point == self.mouse_down):
                self.sticky_bbox = True
                self.selected_bbox.setCursor(QtCore.Qt.OpenHandCursor)

            # update data in annotation_widget
            rect = AnnotationGraphicsView.sceneRectTransform(bbox)

            # clip to scene
            self.verify_rect(rect)
            item_rect = AnnotationGraphicsView.inverseRectTransform(bbox, rect)
            bbox.setRect(item_rect)

            self.moved.emit(rect)

        elif(self.mode == Mode.Resize):
            self.mode = None
            rect = AnnotationGraphicsView.sceneRectTransform(bbox)

            # clip to scene
            self.verify_rect(rect)
            item_rect = AnnotationGraphicsView.inverseRectTransform(bbox, rect)
            bbox.setRect(item_rect)
            # update data store
            self.resized.emit(rect)

        elif(self.mode == Mode.Create):

            self.mode = None
            rect = AnnotationGraphicsView.sceneRectTransform(bbox)
            if(rect.width() < MIN_BOX_SIZE or rect.height() < MIN_BOX_SIZE):
                # just a click, delete box and do click things
                self.mouse_down = None
                self.selected_bbox = None

                # do opposite of these
                self.graphics_scene.removeItem(bbox)
                self.bboxes.pop()

                # just a click on background after sticky?
                # if(self.sticky_bbox):
                #     # deselect sticky box
                #     self.region = None
                #     self.sticky_bbox = False
                #     self.select_bbox.emit(point)
            else:

                # clip to scene
                self.verify_rect(rect)
                item_rect = AnnotationGraphicsView.inverseRectTransform(bbox, rect)
                bbox.setRect(item_rect)
                self.created.emit(rect)

        elif(self.mode == Mode.Delete):
            self.mode = None
            self.delete_event.emit()

    def verify_rect(self, rect):
        if rect.left() < 0:
            rect.setLeft(0.0)
        if rect.top() < 0:
            rect.setTop(0.0)
        if rect.right() > self.sceneRect().right():
            rect.setRight(self.sceneRect().right())
        if rect.bottom() > self.sceneRect().bottom():
            rect.setBottom(self.sceneRect().bottom())

    def wheelEvent(self, event):
        if len(self.scene().items()) > 0:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()

    def zoom_in(self):
        if len(self.scene().items()) > 0:
            self.scale(1.1, 1.1)
            self.zoom_event.emit()

    def zoom_out(self):
        if len(self.scene().items()) > 0:
            self.scale(0.9, 0.9)
            self.zoom_event.emit()

    def resize(self):
        bounding_rect = self.graphics_scene.itemsBoundingRect()
        self.fitInView(bounding_rect, QtCore.Qt.KeepAspectRatio)
        self.setSceneRect(bounding_rect)

    def load_image(self, array):

        self.point = None
        self.graphics_items = []
        self.selected_bbox = None
        self.graphics_scene.clear()
        self.bboxes = []
        h, w, c = array.shape
        self.img_size = (w, h)

        bpl = int(array.nbytes / array.shape[0])
        if array.shape[2] == 4:
            self.qt_image = QtGui.QImage(array.data,
                                         array.shape[1],
                                         array.shape[0],
                                         QtGui.QImage.Format_RGBA8888)
        else:
            self.qt_image = QtGui.QImage(array.data,
                                         array.shape[1],
                                         array.shape[0],
                                         bpl,
                                         QtGui.QImage.Format_RGB888)

        self.graphics_scene.addPixmap(QtGui.QPixmap.fromImage(self.qt_image))

        self.resize()
        #self.setSceneRect(self.graphics_scene.itemsBoundingRect())

    def add_bbox(self, rect, annotation, color, display_details=False):
        brush = QtGui.QBrush(color, QtCore.Qt.SolidPattern)
        pen = QtGui.QPen(brush, BOX_LINE_WIDTH)

        graphics_item = self.graphics_scene.addRect(rect, pen)

        # https://doc.qt.io/qt-5/qt.html#CursorShape-enum
        # graphics_item.setCursor(QtCore.Qt.OpenHandCursor)

        # scale font size based on image resolution
        height = self.img_size[1]
        LABEL_FONT_SIZE = 7  # at 640
        LABEL_FONT_SIZE = int(LABEL_FONT_SIZE * height / 640)
        # display label at top left
        if display_details and annotation is not None:

            font = QtGui.QFont()
            font.setPointSize(int(LABEL_FONT_SIZE))

            text = QtWidgets.QGraphicsTextItem(annotation['label'])
            text.setFont(font)
            text_color = QtCore.Qt.white if color == QtCore.Qt.red else QtCore.Qt.black
            text.setDefaultTextColor(text_color)

            # position above bbox top left corner
            top = rect.top()
            left = rect.left()
            width = text.boundingRect().width()
            height = text.boundingRect().height() # sceneBoundingRect

            text_background = self.graphics_scene.addRect(left, top - height + 8, width-4, height-8, pen, brush)
            text_background.setParentItem(graphics_item)

            text.setPos(left - 2, top - height + 3)
            #text.moveBy(0, -1 * height)

            text.setParentItem(text_background)

        self.bboxes.append(graphics_item)

        return graphics_item

    def nudge_right(self):
        bbox = self.selected_bbox
        if(bbox is None or bbox.sceneBoundingRect().right() >= self.img_size[0]): return False

        self.selected_bbox.moveBy(1, 0)
        self.moved.emit(AnnotationGraphicsView.sceneRectTransform(bbox))
        return True

    def nudge_left(self):
        bbox = self.selected_bbox
        if(bbox is None or bbox.sceneBoundingRect().left() <= 0): return False

        self.selected_bbox.moveBy(-1, 0)
        self.moved.emit(AnnotationGraphicsView.sceneRectTransform(bbox))
        return True

    def nudge_up(self):
        bbox = self.selected_bbox
        if(bbox is None or bbox.sceneBoundingRect().top() <= 0): return False

        self.selected_bbox.moveBy(0, -1)
        self.moved.emit(AnnotationGraphicsView.sceneRectTransform(bbox))
        return True

    def nudge_down(self):
        bbox = self.selected_bbox
        if(bbox is None or bbox.sceneBoundingRect().bottom() >= self.img_size[1]): return False

        self.selected_bbox.moveBy(0, 1)
        self.moved.emit(AnnotationGraphicsView.sceneRectTransform(bbox))
        return True

    def expand_right(self):
        bbox = self.selected_bbox
        if(bbox is None or bbox.sceneBoundingRect().right() >= self.img_size[0]): return False

        rect = bbox.rect()
        rect.setRight(rect.right() + 1)
        self.selected_bbox.setRect(rect)
        self.resized.emit(AnnotationGraphicsView.sceneRectTransform(bbox))
        return True

    def shrink_left(self):
        bbox = self.selected_bbox
        if(bbox is None or bbox.rect().width() <= MIN_BOX_SIZE): return False

        rect = bbox.rect()
        rect.setRight(rect.right() - 1)
        self.selected_bbox.setRect(rect)
        self.resized.emit(AnnotationGraphicsView.sceneRectTransform(bbox))
        return True


    def expand_up(self):
        bbox = self.selected_bbox
        if(bbox is None or bbox.sceneBoundingRect().top() <= 0): return False

        rect = bbox.rect()
        rect.setTop(rect.top() - 1)
        self.selected_bbox.setRect(rect)

        AnnotationGraphicsView.move_label(bbox, 0, -1)
        self.resized.emit(AnnotationGraphicsView.sceneRectTransform(bbox))
        return True

    def shrink_down(self):
        bbox = self.selected_bbox
        if(bbox is None or bbox.rect().height() <= MIN_BOX_SIZE): return False

        rect = bbox.rect()
        rect.setTop(rect.top() + 1)
        self.selected_bbox.setRect(rect)
        AnnotationGraphicsView.move_label(bbox, 0, 1)
        self.resized.emit(AnnotationGraphicsView.sceneRectTransform(bbox))
        return True

    def toggle_visibility(self):

        self.visible = not self.visible
        if self.bboxes:
            for bbox in self.bboxes:
                bbox.setVisible(self.visible)

    def display_bboxes(self, annotations, selected_row, display_details=False):

        if self.bboxes:
            for bbox in self.bboxes:
                self.graphics_scene.removeItem(bbox)
            self.bboxes = []

        if(annotations is None):
            return

        width = self.img_size[0]
        height = self.img_size[1]

        for index, annotation in enumerate(annotations):

            bbox = annotation['bbox']

            x = bbox['xmin'] * width
            y = bbox['ymin'] * height

            top_left = QtCore.QPointF(x, y)

            x = bbox['xmax'] * width
            y = bbox['ymax'] * height

            bottom_right = QtCore.QPointF(x, y)

            rect = QtCore.QRectF(top_left, bottom_right)

            if index == selected_row:
                color = QtCore.Qt.red
            elif (annotation['created_by'] == 'machine' and annotation['updated_by'] == ''):
                color = QtCore.Qt.green
            else:
                color = QtCore.Qt.yellow

            graphics_item = self.add_bbox(rect, annotation, color, display_details)
            graphics_item.setVisible(self.visible)

            if index == selected_row:
                self.selected_bbox = graphics_item
