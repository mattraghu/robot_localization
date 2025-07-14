#!/usr/bin/env python3

"""
A user-friendly ROS 2 launch script that centralizes configuration in a single
place. We define nodes, processes, and arguments in a dictionary so you only
need to modify one area for expansions or tweaks. This script sets up and runs
the usual robot_localization stack, plus an IMU CSV publisher, a message
converter node, and a final bag playback process (with optional delays,
start offsets, and topic remapping).

We use 'rich' for console output to help highlight any issues or successes
in a more visually pleasing way. We'll do minimal try-except blocks for
error detection with a final 'finally' if you want to do cleanup.

We also do the usual docstring for clarity, but keep things fun in comments.
"""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import EnvironmentVariable
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

from rich.console import Console
console = Console()


def generate_launch_description():
    """
    Generate and return a LaunchDescription for the robot localization workflow.
    All node definitions, arguments, and process executions are stored in one
    central 'LAUNCH_CONFIG' dictionary for easy editing. Modify the dictionary,
    and the rest of the code should just work.
    """

    # let's do our single dictionary with everything the user might want to edit
    # bag_files can now specify:
    #   'start_offset' (in seconds),
    #   'remaps' (dict of old_topic:new_topic),
    #   'delay' (in seconds, optional) -> if present, we sleep before playing the bag
    LAUNCH_CONFIG = {
        "environment": {
            "FILE_PATH": None  # we'll fill this at runtime once we know the directory
        },
        "parameter_file_path": "/home/kearfott/ros2_ws/src/robot_localization/params/dual_ekf_navsat_example.yaml",
        "launch_arguments": [
            ("output_final_position", "true"), 
            ("output_location", "~/dual_ekf_navsat_example_debug.txt")
        ],
        "nodes": [
            {
                "name": "static_transform_publisher_node",
                "package": "tf2_ros",
                "executable": "static_transform_publisher",
                "output": "screen",
                "parameters": None,  # not used here
                "remappings": None,
                "arguments": ["0", "0", "0", "0", "0", "0", "1", "base_link", "imu_link"]
            },
            {
                "name": "ekf_filter_node_odom",
                "package": "robot_localization",
                "executable": "ekf_node",
                "output": "screen",
                "parameters": "param_file",  # string "param_file" means "use parameter_file_path"
                "remappings": [("odometry/filtered", "odometry/local")],
                "arguments": None
            },
            {
                "name": "ekf_filter_node_map",
                "package": "robot_localization",
                "executable": "ekf_node",
                "output": "screen",
                "parameters": "param_file",
                "remappings": [("odometry/filtered", "odometry/global")],
                "arguments": None
            },
            {
                "name": "navsat_transform",
                "package": "robot_localization",
                "executable": "navsat_transform_node",
                "output": "screen",
                "parameters": "param_file",
                "remappings": [
                    ("imu/data", "imu/data"),
                    ("gps/fix", "skyline/fix"),
                    ("gps/filtered", "gps/filtered"),
                    ("odometry/gps", "odometry/skyline"),
                    ("odometry/filtered", "odometry/global")
                ],
                "arguments": None
            },
            { 
                "name": "skyline_publisher",
                "package": "skyline_publisher",
                "executable": "skyline_processor.py",
                "output": "screen",
                "parameters": "param_file",
                "remappings": [("imu/data", "imu/data")],
                "arguments": None
            },
            { 
                "name": "image_stamp_converter",
                "package": "skyline_publisher",
                "executable": "image_stamp_converter.py",
                "output": "screen",
                "parameters": "param_file",
                "remappings": [("imu/data", "imu/data")],
                "arguments": None
            },
            {
                "name": "dgps_file_publisher",
                "package": "gnss_publisher",
                "executable": "dgps_file_publisher",
                "output": "log",
                "remappings": [("gps/last_known_fix", "gps/last_known_fix")],
                "parameters": "param_file",
                "arguments": None
            },
            {
                "name": "message_converter_node",
                "package": "message_converter",
                "executable": "republisher",
                "output": "screen",
                "parameters": "param_file",
                "remappings": [
                    ("imu/data", "imu/data"),
                ],
                "arguments": None
            },
            # {

            #     "name": "new_converter_node",
            #     "package": "message_converter",
            #     "executable": "new_converter_node",
            #     "output": "screen",
            #     "parameters": "param_file",
            #     "remappings": [("imu/data", "imu/data")],
            #     "arguments": None
            # },

        ],
        "bag_files": [
            {
                "file_path": "/media/kearfott/PBKFD-104/03_03_2025_skyline_6/03_03_2025_skyline_6_0_remapped.db3/03_03_2025_skyline_6_0_remapped.db3_0.db3",
                "start_offset": 1707.7, # 100.0 i did 1703 BEFORE
                "remaps": {
                    "imu/data": "/mems/raw",
                    "camera/image_raw": "/camera/raw",
                },
                "delay": 1  
            }, 
            # additional bags can go here, for example:
            # {
            #     "file_path": "/path/to/another_bag.db3",
            #     "start_offset": 400,
            #     "remaps": {
            #         "/some/topic": "/other/topic"
            #     },
            #     "delay": 2
            # },
        ]
    }

    # Let's do a quick try-except for environment paths
    try:
        # user wants to find the path from a well-known package
        robot_localization_dir = get_package_share_directory('robot_localization')
        LAUNCH_CONFIG["environment"]["FILE_PATH"] = os.path.join(robot_localization_dir, 'params')
        os.environ["FILE_PATH"] = LAUNCH_CONFIG["environment"]["FILE_PATH"]
    except Exception as e:
        console.log("[bold red]Failed to locate or set environment variable for 'robot_localization' package.[/bold red]")
        console.log(f"[bold red]Error detail: {e}[/bold red]")
        raise
    finally:
        # if you had any open resources or logs to close, you'd do it here
        pass

    # build a list of LaunchArgument actions
    launch_args_actions = []
    for arg_name, default_val in LAUNCH_CONFIG["launch_arguments"]:
        launch_args_actions.append(
            DeclareLaunchArgument(arg_name, default_value=default_val)
        )

    # create Node objects from config
    node_actions = []
    for node_info in LAUNCH_CONFIG["nodes"]:
        # For parameters, we allow the special string "param_file" to mean
        # "use the main parameter_file_path"
        if node_info["parameters"] == "param_file":
            node_info["parameters"] = [LAUNCH_CONFIG["parameter_file_path"]]

        # if there's no parameters, we might pass an empty list
        if node_info["parameters"] is None:
            node_info["parameters"] = []

        # build the Node action
        node_actions.append(
            Node(
                package=node_info["package"],
                executable=node_info["executable"],
                name=node_info["name"],
                output=node_info["output"],
                parameters=node_info["parameters"],
                remappings=node_info["remappings"] if node_info["remappings"] else [],
                arguments=node_info["arguments"] if node_info["arguments"] else []
            )
        )

    # processes for bag files
    process_actions = []
    for bag_info in LAUNCH_CONFIG["bag_files"]:
        # base command
        cmd = ["ros2", "bag", "play", bag_info["file_path"]]

        # optional offset
        offset = bag_info.get("start_offset", None)
        if offset is not None:
            cmd.extend(["--start-offset", str(offset)])

        # optional remaps
        remaps = bag_info.get("remaps", {})
        for old_topic, new_topic in remaps.items():
            cmd.extend(["--remap", f"{old_topic}:={new_topic}"])

        # optional delay
        # if present, we prefix our final command with a 'sleep <delay>' so
        # everything else has time to come up
        delay = bag_info.get("delay", 0)
        if delay < 0:
            console.log("[bold yellow]Ignoring negative delay. That makes no sense, friend![/bold yellow]")
            delay = 0

        if delay > 0:
            # we turn our list into a single string, then prefix 'sleep <delay> &&'
            joined_cmd = " ".join(cmd)
            exec_cmd = f"sleep {delay} && {joined_cmd}"
            process_actions.append(
                ExecuteProcess(
                    cmd=["bash", "-c", exec_cmd],
                    output="screen"
                )
            )
        else:
            # no delay, just run normally
            process_actions.append(
                ExecuteProcess(
                    cmd=cmd,
                    output="screen"
                )
            )

    # now assemble everything into one LaunchDescription 
    return LaunchDescription(
        launch_args_actions + node_actions + process_actions
    )
