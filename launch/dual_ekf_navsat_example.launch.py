# Copyright 2018 Open Source Robotics Foundation, Inc.
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
import launch_ros.actions
import os
from launch.substitutions import EnvironmentVariable
from ament_index_python.packages import get_package_share_directory
import launch.actions

def generate_launch_description():
    robot_localization_dir = get_package_share_directory('robot_localization')
    parameters_file_dir = os.path.join(robot_localization_dir, 'params')
    parameters_file_path = os.path.join(parameters_file_dir, 'dual_ekf_navsat_example.yaml')
    parameters_file_path = "/home/kearfott/ros2_ws/src/robot_localization/params/dual_ekf_navsat_example.yaml"
    os.environ['FILE_PATH'] = str(parameters_file_dir)
    
    return LaunchDescription([
        # Declare launch arguments
        launch.actions.DeclareLaunchArgument(
            'output_final_position',
            default_value='true'),
        launch.actions.DeclareLaunchArgument(
            'output_location',
            default_value='~/dual_ekf_navsat_example_debug.txt'),

        # Static transform publisher
        launch_ros.actions.Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='bl_imu',
            output='screen',
            # arguments=['0', '0', '0', '0', '0', '0.2588', '0.9659', 'base_link', 'imu_link']
            arguments=['0', '0', '0', '0', '0', '0', '1', 'base_link', 'imu_link']
        ),

        # EKF odometry filter node
        launch_ros.actions.Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node_odom',
            output='screen',
            parameters=[parameters_file_path],
            remappings=[('odometry/filtered', 'odometry/local')]
        ),

        # EKF map filter node
        launch_ros.actions.Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node_map',
            output='screen',
            parameters=[parameters_file_path],
            remappings=[('odometry/filtered', 'odometry/global')]
        ),

        # NavSat transform node
        launch_ros.actions.Node(
            package='robot_localization',
            executable='navsat_transform_node',
            name='navsat_transform',
            output='screen',
            parameters=[parameters_file_path],
            remappings=[
                ('imu/data', 'imu/data'),
                ('gps/fix', 'gps/fix'),
                ('gps/filtered', 'gps/filtered'),
                ('odometry/gps', 'odometry/gps'),
                ('odometry/filtered', 'odometry/global')
            ]
        ),

        # Play ROS 2 bag file
        launch.actions.ExecuteProcess(
            cmd=[
                'ros2', 'bag', 'play', 
                # '/home/kearfott/ros2_ws/FIRSTVANRUN/FIRSTVANRUN_0.db3',
                # '--start-offset', '190',
                # '--remap', 
                # '/imu/data:=/imu',
                # '/gps_ios:=/gpsiosidk',
                # '/gps_fix:=/idk',
                '/home/kearfott/ros2_ws/SECOND_VAN_RUN_NEWER/SECOND_VAN_RUN_NEWER_0.db3',
                '--start-offset', '400',
                '--remap', 
                '/imu/data:=/imu',
                '/gps_ios:=/gpsiosidk',
                '/gps_fix:=/idk',

            ],
            output='screen'
        )
    ])
