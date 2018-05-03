#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import rospy
import rospkg
import yaml
import codecs
from math import atan2, cos, sin, pi, atan
from pyquaternion import Quaternion

from rqt_simulation_msgs.msg import Sense, Edge
from geometry_msgs.msg import Pose

from qt_gui.plugin import Plugin
from python_qt_binding import loadUi
from python_qt_binding.QtWidgets import QWidget, QLabel, QApplication, QDialog, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QVBoxLayout, QGridLayout, QRadioButton, QGroupBox, QCheckBox, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem, QFileDialog
from python_qt_binding.QtCore import QTimer, QEvent, pyqtSignal, QPointF, QRectF, QSizeF, QLineF, Slot, pyqtSlot, Qt
from python_qt_binding.QtGui import QImageReader, QImage, QPixmap, QMouseEvent, QPen, QBrush, QColor, QFont

class Change_FTS_dialog(QDialog):
    def __init__(self, current_graphicsScene, FTS):
        super(Change_FTS_dialog, self).__init__()
        self.setObjectName('Change_FTS_dialog')

        # Copy graphics scene
        self.graphicsScene = current_graphicsScene
        # Copy FTS
        self.FTS = FTS

        # Load ui file
        ui_file = os.path.join(rospkg.RosPack().get_path('rqt_simulation'), 'resource', 'change_FTS.ui')
        loadUi(ui_file, self)

        # Publisher for Sense message
        self.sense_pub = rospy.Publisher('/environment', Sense, queue_size=1)

        # Set dialog layout to grid
        self.grid = QGridLayout()

        # Initialize variables for FTS matrix
        self.groupBox_list = []
        self.FTS_matrix = []
        self.vbox_list = []
        self.vbox = QVBoxLayout()

        # Sort the ROI's alphabetic, needed for FTS matrix since it's implemented with list
        sorted_keys = self.FTS.region_of_interest.keys()
        sorted_keys.sort()

        # Set the ROI's and edges from previous selection
        for i in range(0, self.graphicsScene.regionCounter):
            groupBox = QGroupBox(sorted_keys[i])
            self.groupBox_list.append(groupBox)
            checkBox_list = []
            self.FTS_matrix.append(checkBox_list)

            vbox = QVBoxLayout()
            self.vbox_list.append(vbox)
            for j in range(0, self.graphicsScene.regionCounter):
                self.FTS_matrix[i].append(QCheckBox('r' + str(j+1).zfill(2)))
                self.FTS_matrix[i][j].stateChanged.connect(self.edge_both_ways)
                self.vbox_list[i].addWidget(self.FTS_matrix[i][j])

            self.groupBox_list[i].setLayout(self.vbox_list[i])
            self.grid.addWidget(self.groupBox_list[i], 0, i+1, Qt.AlignRight)

        for i in range(0, self.graphicsScene.regionCounter):
            for j in range(0, self.graphicsScene.regionCounter):
                if (str(i+1) + '-' + str(j+1)) in self.graphicsScene.line_dict.keys():
                    self.FTS_matrix[i][j].setCheckState(2)

        # Variable is True is left mouse button is holded
        self.clicked = False

        # Make whole dialog scrollable
        self.scrollAreaWidgetContents.setLayout(self.grid)

        # Connect all functions with corresponding functions
        self.graphicsScene.signalMousePressedPos.connect(self.pointSelection)
        self.graphicsScene.signalMouseReleasedPos.connect(self.pointRelease)
        self.graphicsScene.signalMouseMovePos.connect(self.mouseMove)

        # Load graphics scene in graphics view
        self.graphicsView.setScene(self.graphicsScene)




    # Save the current FTS in yaml file
    @Slot(bool)
    def on_button_FTS_save_pressed(self):
        self.button_save_FTS.setEnabled(False)
        sorted_keys = self.FTS.region_of_interest.keys()
        sorted_keys.sort()
        for i in range(0, len(self.FTS_matrix)):
            self.FTS.region_of_interest[sorted_keys[i]]['edges'] = []
            for j in range(0, len(self.FTS_matrix[0])):
                if (self.FTS_matrix[i][j].checkState() == 2):
                    self.FTS.add_edge(sorted_keys[i], sorted_keys[j], cost=1.0)

        print('start saving')
        data = {'FTS' : self.FTS.region_of_interest}
        print(data)
        env_file = os.path.join(rospkg.RosPack().get_path('rqt_simulation'), 'config', 'FTS', 'env_GUI.yaml')
        with codecs.open(env_file, 'w', encoding='utf-8') as outfile:
            yaml.safe_dump(data, outfile, default_flow_style=False)

        self.accept()

    # Reset FTS
    @Slot(bool)
    def on_button_reset_pressed(self):
        print('Reset')

        for i in range(0, self.graphicsScene.regionCounter):
            self.grid.removeWidget(self.groupBox_list[0])
            self.groupBox_list[0].deleteLater()
            del self.groupBox_list[0]

        self.graphicsScene.reset()
        self.vbox = QVBoxLayout()
        self.vbox_list = []
        self.FTS_matrix = []
        self.FTS.region_of_interest = {}
        self.button_save_FTS.setEnabled(False)

    # Remove last added ROI
    @Slot(bool)
    def remove_last_ROI(self):
        del self.FTS_matrix[self.graphicsScene.regionCounter-1]
        del self.FTS.region_of_interest['r' + str(self.graphicsScene.regionCounter).zfill(2)]
        del self.vbox_list[self.graphicsScene.regionCounter-1]

        self.grid.removeWidget(self.groupBox_list[self.graphicsScene.regionCounter-1])
        self.groupBox_list[self.graphicsScene.regionCounter-1].deleteLater()
        del self.groupBox_list[self.graphicsScene.regionCounter-1]

        for i in range(0, self.graphicsScene.regionCounter-1):
            self.vbox_list[i].removeWidget(self.FTS_matrix[i][self.graphicsScene.regionCounter-1])
            self.FTS_matrix[i][self.graphicsScene.regionCounter-1].deleteLater()
            del self.FTS_matrix[i][self.graphicsScene.regionCounter-1]
            if self.graphicsScene.regionCounter < (i+1):
                if ((str(self.graphicsScene.regionCounter) + '-' + str(i+1)) in self.graphicsScene.line_dict.keys()):
                    self.graphicsScene.remove_edge((str(self.graphicsScene.regionCounter) + '-' + str(i+1)))
            else:
                if ((str(i+1) + '-' + str(self.graphicsScene.regionCounter)) in self.graphicsScene.line_dict.keys()):
                    self.graphicsScene.remove_edge((str(i+1) + '-' + str(self.graphicsScene.regionCounter)))

        self.graphicsScene.remove_ROI()

        if self.graphicsScene.regionCounter < 1:
            self.button_ROI.setEnabled(False)

    # Sets all edges between ROI's
    @Slot(bool)
    def on_button_set_edges_pressed(self):
        for i in range(0, len(self.FTS_matrix)):
            for j in range(0, len(self.FTS_matrix[0])):
                self.FTS_matrix[i][j].setCheckState(Qt.Checked)

    # Removes all edges between ROI's
    @Slot(bool)
    def delete_edges(self):
        for i in range(0, len(self.FTS_matrix)):
            for j in range(0, len(self.FTS_matrix[0])):
                self.FTS_matrix[i][j].setCheckState(Qt.Unchecked)


    # Add ROI with mouse click
    def pointSelection(self, pos):
        print('scene')
        print(pos)
        self.clicked = True
        self.current_arrow = []
        self.graphicsScene.add_ROI(pos)
        print(self.graphicsScene.regionCounter)
        self.pose_of_interest = {'position' : self.graphicsScene.pixelToWorld(pos)}
        print(self.graphicsScene.pixelToWorld(pos))

        regionString = 'r' + str(self.graphicsScene.regionCounter).zfill(2)

        groupBox = QGroupBox(regionString)
        self.groupBox_list.append(groupBox)
        checkBox_list = []
        self.FTS_matrix.append(checkBox_list)

        vbox = QVBoxLayout()
        self.vbox_list.append(vbox)
        for i in range(0, self.graphicsScene.regionCounter):
            if i == (self.graphicsScene.regionCounter-1):
                for j in range(0, i+1):
                    self.FTS_matrix[i].append(QCheckBox('r' + str(j+1).zfill(2)))
                    self.FTS_matrix[i][j].stateChanged.connect(self.edge_both_ways)
                    self.vbox_list[i].addWidget(self.FTS_matrix[i][j])
            else:
                self.FTS_matrix[i].append(QCheckBox('r' + str(self.graphicsScene.regionCounter).zfill(2)))
                self.FTS_matrix[i][self.graphicsScene.regionCounter-1].stateChanged.connect(self.edge_both_ways)
                self.vbox_list[i].addWidget(self.FTS_matrix[i][self.graphicsScene.regionCounter-1])

        for i in range(0, len(self.groupBox_list)):
            self.groupBox_list[i].setLayout(self.vbox_list[i])
            self.grid.addWidget(self.groupBox_list[i], 0, i+1, Qt.AlignRight)

    # Set orientation of ROI by releasing mouse button
    def pointRelease(self, pos):
        self.clicked = False
        pixel_coords = self.graphicsScene.items_dict['r' + str(self.graphicsScene.regionCounter).zfill(2)]['pixel_coords']
        deltay = -pos.y() + pixel_coords.y()
        deltax = pos.x() - pixel_coords.x()
        theta = atan2(deltay, deltax)
        quat = Quaternion(axis=(0.0, 0.0, 1.0), radians=theta)
        self.pose_of_interest.update({'orientation' : (float(quat[0]), float(quat[1]), float(quat[2]), float(quat[3]))})
        edges = []
        self.FTS.add_region('r' + str(self.graphicsScene.regionCounter).zfill(2), edges, pose = self.pose_of_interest)
        self.graphicsScene.items_dict['r' + str(self.graphicsScene.regionCounter).zfill(2)].update({'arrow' : self.current_arrow})

    # Update orientation arrow while mouse button is pressed
    def mouseMove(self, pos):
        arrow_length = 50
        if self.clicked:
            pixel_coords = self.graphicsScene.items_dict['r' + str(self.graphicsScene.regionCounter).zfill(2)]['pixel_coords']
            theta = atan2((pos.y() - pixel_coords.y()) , (pos.x() - pixel_coords.x()))
            end_point = QPointF(pixel_coords.x() + arrow_length * cos(theta), pixel_coords.y() + arrow_length * sin(theta))
            if len(self.current_arrow) > 0:
                self.graphicsScene.removeArrow(self.current_arrow)
            self.current_arrow = self.graphicsScene.addArrow(pixel_coords, end_point)

    # Set the edges both ways in FTS matrix
    @Slot(bool)
    def edge_both_ways(self, state):
        sense_msg = Sense()
        for i in range(0, self.graphicsScene.regionCounter):
            for j in range(0, self.graphicsScene.regionCounter):
                if self.FTS_matrix[i][j].checkState() != self.FTS_matrix[j][i].checkState():
                    start_pose = self.from_dict_to_pose_msg('r' + str(i+1).zfill(2))
                    target_pose = self.from_dict_to_pose_msg('r' + str(j+1).zfill(2))

                    if state == 2:
                        edge = self.build_edge_msg(start_pose, target_pose, 1.0, True)
                        sense_msg.edges.append(edge)
                        edge = self.build_edge_msg(target_pose, start_pose, 1.0, True)
                        sense_msg.edges.append(edge)

                        self.FTS_matrix[j][i].setCheckState(2)
                        if i < j:
                            if (str(i+1) + '-' + str(j+1)) not in self.graphicsScene.line_dict.keys():
                                self.graphicsScene.add_edge(i+1, j+1)
                                print((str(i+1) + '-' + str(j+1)))                                
                        else:
                            if (str(j+1) + '-' + str(i+1)) not in self.graphicsScene.line_dict.keys():
                                self.graphicsScene.add_edge(j+1, i+1)
                                print((str(j+1) + '-' + str(i+1)))

                    elif state == 0:
                        edge = self.build_edge_msg(start_pose, target_pose, 1.0, False)
                        sense_msg.edges.append(edge)
                        edge = self.build_edge_msg(target_pose, start_pose, 1.0, False)
                        sense_msg.edges.append(edge)
                        print((str(i+1) + '-' + str(j+1)))
                        self.FTS_matrix[j][i].setCheckState(0)
                        if i < j:
                            if (str(i+1) + '-' + str(j+1)) in self.graphicsScene.line_dict.keys():
                                self.graphicsScene.remove_edge(str(i+1) + '-' + str(j+1))
                        else:
                            if (str(j+1) + '-' + str(i+1)) in self.graphicsScene.line_dict.keys():
                                self.graphicsScene.remove_edge(str(j+1) + '-' + str(i+1))

        self.sense_pub.publish(sense_msg)

    # Cancel map dialog
    @Slot(bool)
    def on_button_cancel_pressed(self):
        self.on_button_reset_pressed()
        self.accept()

    def from_dict_to_pose_msg(self, roi_label):
        pose_msg = Pose()
        pose_msg.position.x = self.FTS.region_of_interest[roi_label]['pose']['position'][0]
        pose_msg.position.y = self.FTS.region_of_interest[roi_label]['pose']['position'][1]
        pose_msg.position.z = self.FTS.region_of_interest[roi_label]['pose']['position'][2]
        pose_msg.orientation.w = self.FTS.region_of_interest[roi_label]['pose']['orientation'][0]
        pose_msg.orientation.x = self.FTS.region_of_interest[roi_label]['pose']['orientation'][1]
        pose_msg.orientation.y = self.FTS.region_of_interest[roi_label]['pose']['orientation'][2]
        pose_msg.orientation.z = self.FTS.region_of_interest[roi_label]['pose']['orientation'][3]

        return pose_msg

    def build_edge_msg(self, start_pose, target_pose, weight, add):
        edge = Edge()
        edge.start_pose = start_pose
        edge.target_pose = target_pose
        edge.add.data = add
        edge.weight = weight

        return edge

    # Load FTS from a yaml file
    @Slot(bool)
    def load_FTS(self):
        # Start file dialog
        directory = os.path.join(rospkg.RosPack().get_path('rqt_simulation'), 'config', 'FTS')
        File_dialog = QFileDialog(directory=directory, filter='.yaml')
        FTS_file = File_dialog.getOpenFileName()
        print(FTS_file[0])
        stream = file(FTS_file[0], 'r')
        data = yaml.load(stream)

        # Reset graphics Scene
        self.graphicsScene.reset()

        # Load FTS
        self.FTS.region_of_interest = {}
        self.FTS.region_of_interest = data['FTS']
        sorted_keys = self.FTS.region_of_interest.keys()
        sorted_keys.sort()
        stream.close()      

        arrow_length = 50

        # Add all the ROI's and edges
        for i in range(0, len(self.FTS.region_of_interest)):
            region_string = 'r' + str(i+1).zfill(2)
            pixel_coords = self.graphicsScene.worldToPixel(self.FTS.region_of_interest[sorted_keys[i]]['pose']['position'])
            self.graphicsScene.add_ROI(pixel_coords)

            quaternion = Quaternion(self.FTS.region_of_interest[sorted_keys[i]]['pose']['orientation'])
            rot_axis = quaternion.axis
            theta = quaternion.angle * rot_axis[2]
            end_point = QPointF(pixel_coords.x() + arrow_length * cos(theta), pixel_coords.y() - arrow_length * sin(theta))
            arrow = self.graphicsScene.addArrow(pixel_coords, end_point)
            self.graphicsScene.items_dict[region_string]['arrow'] = arrow

            groupBox = QGroupBox(sorted_keys[i])
            self.groupBox_list.append(groupBox)
            checkBox_list = []
            self.FTS_matrix.append(checkBox_list)

            vbox = QVBoxLayout()
            self.vbox_list.append(vbox)

            for j in range(0, len(self.FTS.region_of_interest)):
                    self.FTS_matrix[i].append(QCheckBox(sorted_keys[j]))
                    self.FTS_matrix[i][j].stateChanged.connect(self.edge_both_ways)
                    self.vbox_list[i].addWidget(self.FTS_matrix[i][j])

            self.groupBox_list[i].setLayout(self.vbox_list[i])
            self.grid.addWidget(self.groupBox_list[i], 0, i+1, Qt.AlignRight)

        for i in range(0, len(self.FTS.region_of_interest)):
            for j in range(0, len(self.FTS.region_of_interest[sorted_keys[i]]['edges'])):
                index = sorted_keys.index(self.FTS.region_of_interest[sorted_keys[i]]['edges'][j]['target'])
                self.FTS_matrix[i][index].setCheckState(2)
