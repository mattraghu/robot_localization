#!/usr/bin/env python3
# ---
#                                ROS 2 LAUNCH: DICT-DRIVEN EDITION
# ---

"""
Centralised, one-stop-shop launch file.

• Three static transforms:
    ▸  base_link ➞ imu_link   (identity, keeps TF happy)
    ▸  map       ➞ camera_init  (camera frame anchored to map)
    ▸  base_link ➞ body         (legacy frame rename)

• Dual EKF nodes (local + global) and NavSat Transform.
• Extra helper nodes (converter, Skyline, etc.) left in for convenience.
• Bag-file playback section handles offsets, remaps & optional delays.

Tweak the LAUNCH_CONFIG dict ↓ and everything else Just Works™.

Author: Matthew Raghunandan
"""

# ---
#                                IMPORTS
# ---

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from rich.console import Console

console = Console()

# ---
#                                CONFIG DICTIONARY
# ---

LAUNCH_CONFIG = {
    # Will be filled in at runtime once we locate the package
    "environment": {"FILE_PATH": None},

    # Parameter YAML (updated at runtime to absolute path)
    "parameter_file_path": "senior_design_24_25_2.yaml",

    # Declared command-line launch arguments
    "launch_arguments": [
        ("output_final_position", "true"),
        ("output_location", "~/dual_ekf_navsat_example_debug.txt"),
    ],

    # Nodes to spin up 🚀
    "nodes": [
        # ---------- STATIC TRANSFORMS ----------
        {
            "name": "static_tf_base_to_imu",
            "package": "tf2_ros",
            "executable": "static_transform_publisher",
            "output": "screen",
            "parameters": None,
            "remappings": None,
            # "arguments": ["0", "0", "0", "0.7071", "0", "0", "0.7071", "base_link", "imu_link"],
            "arguments": ["0", "0", "0", "0", "0", "0", "1", "base_link", "imu_link"],

            # static_transforms:
            #   child_frame_id: imu_link
            #     parent_frame_id: base_link
            #     translation:
            #     x: -0.067
            #     y: 0.019
            #     z: 0.110
            #     rotation:
            #     x: -0.5
            #     y: -0.5
            #     z: -0.5
            #     w:  0.5
            # "arguments": ["-0.067", "0.019", "0.110", "-0.5", "-0.5", "-0.5", "0.5", "base_link", "imu_link"],

        },
        {
            "name": "static_tf_gps_to_base_link",
            "package": "tf2_ros",
            "executable": "static_transform_publisher",
            "output": "screen",
            "parameters": None,
            "remappings": None,
            "arguments": ["0", "0", "0", "0", "0", "0", "base_link", "gps"],
        },

        # ---------- ROBOT_LOCALIZATION STACK ----------
        {
            "name": "ekf_filter_node_odom",
            "package": "robot_localization",
            "executable": "ekf_node",
            "output": "screen",
            "parameters": "param_file",
            "remappings": [("odometry/filtered", "odometry/local")],
            "arguments": None,
        },
        {
            "name": "ekf_filter_node_map",
            "package": "robot_localization",
            "executable": "ekf_node",
            "output": "screen",
            "parameters": "param_file",
            "remappings": [("odometry/filtered", "odometry/global")],
            "arguments": None,
        },
        {
            "name": "navsat_transform",
            "package": "robot_localization",
            "executable": "navsat_transform_node",
            "output": "screen",
            "parameters": "param_file",
            "remappings": [
                ("imu/data", "imu/data"),
                ("gps/fix", "gps/fix"),
                ("gps/filtered", "gps/filtered"),
                ("odometry/gps", "odometry/gps"),
                ("odometry/filtered", "odometry/global"),
            ],
            "arguments": None,
        },

        # ---------- OPTIONAL UTILITY NODES ----------
        # {
        #     "name": "new_converter_node",
        #     "package": "message_converter",
        #     "executable": "new_converter_node",
        #     "output": "screen",
        #     "parameters": "param_file",
        #     "remappings": [("imu/data", "imu/data")],
        #     "arguments": None,
        # },
    ],

    # Bag-file playback definitions 🎞️
    "bag_files": [
        {
            "file_path": "/media/kearfott/PBKFD-104/stevenzrun7/zip681b67c93ed86/jknuckle@stevens.edu-ae7uY9sQ_317MIjdubN/good_slam5/good_slam5_0.db3",
            "start_offset": 0.0,
            "delay": 1.0,
            "blacklist": [ 
                "/tf",
            ],
            "remaps": {
                "imu/data" : "imu/raw",
                "slam/odometry" : "slam/odometry/raw",
            }
        },
    ],
}

# ---
#                                LAUNCH BUILDER
# ---

def generate_launch_description() -> LaunchDescription:
    """
    Convert the LAUNCH_CONFIG dictionary into a LaunchDescription.
    """

    # --- Resolve parameter file path & env var ---
    try:
        rl_dir = get_package_share_directory("robot_localization")
        LAUNCH_CONFIG["environment"]["FILE_PATH"] = os.path.join(rl_dir, "params")
        os.environ["FILE_PATH"] = LAUNCH_CONFIG["environment"]["FILE_PATH"]

        LAUNCH_CONFIG["parameter_file_path"] = os.path.join(
            rl_dir, "params", LAUNCH_CONFIG["parameter_file_path"]
        )
        console.print(
            f"[green]Parameter file:[/green] {LAUNCH_CONFIG['parameter_file_path']}"
        )
    except Exception as e:
        console.print(
            f"[bold red]Could not locate robot_localization package![/bold red] 😵\n{e}"
        )
        raise

    # --- Launch arguments ---
    launch_args = [
        DeclareLaunchArgument(name, default_value=val)
        for name, val in LAUNCH_CONFIG["launch_arguments"]
    ]

    # --- Nodes ---
    node_actions = []
    for info in LAUNCH_CONFIG["nodes"]:
        # Swap in the param YAML path if requested
        params = (
            [LAUNCH_CONFIG["parameter_file_path"]]
            if info["parameters"] == "param_file"
            else (info["parameters"] or [])
        )

        node_actions.append(
            Node(
                package=info["package"],
                executable=info["executable"],
                name=info["name"],
                output=info["output"],
                parameters=params,
                remappings=info.get("remappings", []),
                arguments=info.get("arguments", []),
            )
        )

    # --- Bag-play processes ---
    process_actions = []
    for bag in LAUNCH_CONFIG["bag_files"]:
        cmd = ["ros2", "bag", "play", bag["file_path"]]

        if "start_offset" in bag:
            cmd += ["--start-offset", str(bag["start_offset"])]

        if bag.get("remaps"):
            cmd.append("--remap")
            # Define remaps
            for old, new in bag["remaps"].items():
                cmd.append(f"{old}:={new}")

        # Blacklist topics  
        if bag.get("blacklist"):
            for topic in bag["blacklist"]:
                cmd.append(f"{topic}:={topic+'/blacklist'}")

        delay = bag.get("delay", 0.0)
        if delay and delay > 0:
            exec_cmd = f"sleep {delay} && {' '.join(cmd)}"
            cmd = ["bash", "-c", exec_cmd]


        process_actions.append(
            ExecuteProcess(cmd=cmd, output="screen", emulate_tty=True)
        )

    # --- Assemble everything ---
    return LaunchDescription(launch_args + node_actions + process_actions)

# ---
#                                END OF FILE
# ---