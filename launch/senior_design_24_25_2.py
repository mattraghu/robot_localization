#!/usr/bin/env python3
# =============================================================
#        ROS 2 LAUNCH — MAX-PUMP *DICT-DRIVEN* EDITION 🏋️‍♂️
#  One file to curl them all: static TFs, dual EKFs, NavSat,
#  optional utility nodes, **and** bag-file playback with
#  remap-based blacklisting (no --exclude-topics, per bro’s spec).
#
#  Keep the swagger, keep the logic — zero functional drift. 🔥
#
#  Author: Matthew Raghunandan
# =============================================================

# -
#                           IMPORTS
# -
import os
from typing import Dict, Any, List

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from rich.console import Console

console = Console(highlight=False)

# -
#                       CONFIG DICTIONARY
# -
LAUNCH_CONFIG: Dict[str, Any] = {
    # Will get filled at runtime when we resolve the package path
    "environment": {"FILE_PATH": None},

    # Param YAML (relative to robot_localization/params)
    "parameter_file_path": "senior_design_24_25_2.yaml",

    # CLI launch arguments (name, default)
    "launch_arguments": [
        ("output_final_position", "true"),
        ("output_location", "~/dual_ekf_navsat_example_debug.txt"),
    ],

    # Nodes to spin up — add/remove at will
    "nodes": [
        # ---------- STATIC TRANSFORMS ----------
        # base_link ➜ imu_link  (identity quat)
        {
            "name":        "static_tf_base_to_imu",
            "package":     "tf2_ros",
            "executable":  "static_transform_publisher",
            "arguments":   ["0", "0", "0", "0", "0", "0", "1", "base_link", "imu_link"],
        },
        # map ➜ camera_init (anchor camera to map)
        {
            "name":        "static_tf_map_to_camera_init",
            "package":     "tf2_ros",
            "executable":  "static_transform_publisher",
            "arguments":   ["0", "0", "0", "0", "0", "0", "1", "map", "camera_init"],
        },
        # base_link ➜ body  (legacy alias; zero rot & trans)
        {
            "name":        "static_tf_base_to_body",
            "package":     "tf2_ros",
            "executable":  "static_transform_publisher",
            # NB: only 6 args ⇒ implicit unit-quat (0 0 0 1)
            "arguments":   ["0", "0", "0", "0", "0", "0", "base_link", "body"],
        },
        # base_link ➜ gps  (identity quat)
        {
            "name":        "static_tf_base_to_gps",
            "package":     "tf2_ros",
            "executable":  "static_transform_publisher",
            "arguments":   ["0", "0", "0", "0", "0", "0", "1", "base_link", "gps"],
        },

        # ---------- ROBOT_LOCALIZATION STACK ----------
        {
            "name":        "ekf_filter_node_odom",
            "package":     "robot_localization",
            "executable":  "ekf_node",
            "parameters":  "param_file",
            "remappings":  [("odometry/filtered", "odometry/local")],
        },
        {
            "name":        "ekf_filter_node_map",
            "package":     "robot_localization",
            "executable":  "ekf_node",
            "parameters":  "param_file",
            "remappings":  [("odometry/filtered", "odometry/global")],
        },
        {
            "name":        "navsat_transform",
            "package":     "robot_localization",
            "executable":  "navsat_transform_node",
            "parameters":  "param_file",
            "remappings": [
                ("imu/data",          "imu/data"),
                ("gps/fix",           "gps/fix"),
                ("gps/filtered",      "gps/filtered"),
                ("odometry/gps",      "odometry/gps"),
                ("odometry/filtered", "odometry/global"),
            ],
        },

        # ---------- OPTIONAL NODES (commented out) ----------
        # {
        #     "name":        "new_converter_node",
        #     "package":     "message_converter",
        #     "executable":  "new_converter_node",
        #     "parameters":  "param_file",
        #     "remappings":  [("imu/data", "imu/data")],
        # },
    ],

    # 🎞️  Bag-file playback configs
    "bag_files": [
        {
            "file_path":   "/media/kearfott/PBKFD-104/stevenzrun7/zip681b67c93ed86/"
                            "jknuckle@stevens.edu-ae7uY9sQ_317MIjdubN/"
                            "good_slam5/good_slam5_0.db3",
            "start_offset": 0.0,
            "delay":        1.0,          # bash sleep delay (sec)
            # Topics we *don’t* want → remap to throwaway names
            "blacklist": ["/tf"],
            # Remaps we *do* want
            "remaps": {
                "imu/data":      "imu/raw",
                "slam/odometry": "slam/odometry/raw",
            },
        },
    ],
}

# Helper ---------------------------------------------------------------------


def _resolve_param_file() -> str:
    """Locate robot_localization params directory & return absolute YAML path."""
    rl_dir = get_package_share_directory("robot_localization")
    param_dir = os.path.join(rl_dir, "params")
    LAUNCH_CONFIG["environment"]["FILE_PATH"] = param_dir
    os.environ["FILE_PATH"] = param_dir   # export for any node that cares

    abs_yaml = os.path.join(param_dir, LAUNCH_CONFIG["parameter_file_path"])
    if not os.path.isfile(abs_yaml):
        raise FileNotFoundError(f"Param YAML not found: {abs_yaml}")

    console.print(f"[bold green]Param YAML:[/bold green] {abs_yaml}")
    return abs_yaml


def _make_node(cfg: Dict[str, Any], param_yaml: str) -> Node:
    """Convert a node-dict into a launch_ros Node action."""
    params = [param_yaml] if cfg.get("parameters") == "param_file" else cfg.get("parameters", [])
    return Node(
        package=cfg["package"],
        executable=cfg["executable"],
        name=cfg["name"],
        output="screen",
        parameters=params,
        remappings=cfg.get("remappings", []),
        arguments=cfg.get("arguments", []),
    )


def _make_bag_process(bag: Dict[str, Any]) -> ExecuteProcess:
    """Turn bag-file dict into an ExecuteProcess (with remap blacklisting)."""
    cmd: List[str] = ["ros2", "bag", "play", bag["file_path"]]

    if bag.get("start_offset") is not None:
        cmd += ["--start-offset", str(bag["start_offset"])]

    # Positive remaps
    if bag.get("remaps"):
        cmd.append("--remap")
        for old, new in bag["remaps"].items():
            cmd.append(f"{old}:={new}")

    # Blacklist ⇒ remap to <topic>/blacklist  (works on every ROS 2 distro)
    for topic in bag.get("blacklist", []):
        cmd += ["--remap", f"{topic}:={topic}/blacklist"]

    # Optional bash wrapper to delay playback
    delay = bag.get("delay", 0.0)
    if delay and delay > 0:
        cmd = ["bash", "-c", f"sleep {delay} && {' '.join(cmd)}"]

    return ExecuteProcess(cmd=cmd, output="screen", emulate_tty=True)


# Launch builder -------------------------------------------------------------


def generate_launch_description() -> LaunchDescription:
    """Build and return the Gym-Bro LaunchDescription 💪."""
    try:
        param_yaml = _resolve_param_file()
    except Exception as exc:
        console.print(f"[bold red]Failed to resolve param file![/bold red] 🤕\n{exc}")
        raise

    # Declare CLI args
    cli_args = [
        DeclareLaunchArgument(name, default_value=val) for name, val in LAUNCH_CONFIG["launch_arguments"]
    ]

    # Nodes
    node_actions = [_make_node(n, param_yaml) for n in LAUNCH_CONFIG["nodes"]]

    # Bag processes
    bag_actions = [_make_bag_process(bag) for bag in LAUNCH_CONFIG["bag_files"]]

    # Assemble & return
    return LaunchDescription(cli_args + node_actions + bag_actions)


# -------------------------------------------------------------
#                          END OF FILE
#                     Time to go to the gym! 🚀
# -------------------------------------------------------------
