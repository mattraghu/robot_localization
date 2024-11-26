# Copyright 2018 Open Source Robotics Foundation, Inc.
# Copyright 2019 Samsung Research America
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from launch import LaunchDescription
from ament_index_python.packages import get_package_share_directory
import launch_ros.actions
import os
import yaml
from launch.substitutions import EnvironmentVariable
import pathlib
import launch.actions
from launch.actions import DeclareLaunchArgument

def generate_launch_description():
    return LaunchDescription([
        # Static transform publisher
        launch_ros.actions.Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='bl_imu',
            output='screen',
            # arguments=['0', '0', '0', '0', '0', '0.2588', '0.9659', 'base_link', 'imu_link']
            arguments=['0', '0', '0', '0', '0', '0', '1', 'base_link', 'imu_link']
        ),
        launch_ros.actions.Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node_map',
            output='screen',
            parameters=[os.path.join(get_package_share_directory("robot_localization"), 'params', 'ekf.yaml')],
            remappings=[('odometry/filtered', 'odometry/global')]
           ),
        launch_ros.actions.Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node_odom',
            output='screen',
            parameters=[os.path.join(get_package_share_directory("robot_localization"), 'params', 'ekf.yaml')],
            remappings=[('odometry/filtered', 'odometry/local')]
           ),

        # NavSat transform node
        launch_ros.actions.Node(
            package='robot_localization',
            executable='navsat_transform_node',
            name='navsat_transform',
            output='screen',
            parameters=[os.path.join(get_package_share_directory("robot_localization"), 'params', 'ekf.yaml')],
            remappings=[
                ('imu/data', 'imu/data'),
                ('gps/fix', 'gps/fix'),
                ('gps/filtered', 'gps/filtered'),
                ('odometry/gps', 'odometry/gps'),
                ('odometry/filtered', 'odometry/global')
            ]
        ),

        # Bag file
        launch.actions.ExecuteProcess(
            cmd=[
                'ros2', 'bag', 'play', 
                '/home/kearfott/ros2_ws/FIRSTVANRUN/FIRSTVANRUN_0.db3',
                '--start-offset', '190',
                '--remap', 
                '/imu/data:=/imu',
                '/gps_ios:=/gps',
                '/gps_fix:=/idk'
            ],
            output='screen'
        )
])
