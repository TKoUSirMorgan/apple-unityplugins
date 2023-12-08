#! /usr/bin/env python3
# Requirements: Xcode, Xcode Command Line tools, npm, python3
import argparse, pathlib

import scripts.upi_utility as utility
import scripts.upi_unity_native_plugin_manager as plugin_manager
import scripts.upi_toolchain as toolchain

from datetime import datetime
from pathlib import Path

from scripts.upi_cli_argument_options import PluginID, PlatformID, ConfigID, BuildActionID, CleanActionID
from scripts.upi_build_context import BuildContext
from scripts.upi_utility import PromptColor, Printer

# Set a script version to track evolution
build_script_version = "2.0.0"

# -----------------
# Prompt Formatting

prompt_theme = utility.PromptTheme()

# Set to false to disable all colors in your terminal emulator.
prompt_theme_enable = True

# These colors control the colors that the script uses in your terminal emulator.
if prompt_theme_enable:
    # Control the color of standard messages
    prompt_theme.standard_output_color = PromptColor.NONE

    # Color for section headings in output
    prompt_theme.section_heading_color = PromptColor.BRIGHT_BLUE

    # Color used when the script reports status
    prompt_theme.status_color = PromptColor.GREEN

    # Color used when the script adds context, such as a file path or version number, to a message
    prompt_theme.context_color = PromptColor.MAGENTA

    # Error tags
    prompt_theme.error_bg_color = PromptColor.BG_RED
    prompt_theme.error_color = PromptColor.BRIGHT_WHITE

    # Warning tags
    prompt_theme.warning_bg_color = PromptColor.BG_BRIGHT_YELLOW
    prompt_theme.warning_color = PromptColor.BLACK

    # Info tags
    prompt_theme.info_bg_color = PromptColor.BG_BLACK
    prompt_theme.info_color = PromptColor.GREEN

    # Colors used when user input is prompted
    prompt_theme.user_input_bg_color = PromptColor.BG_BLUE
    prompt_theme.user_input_color = PromptColor.BRIGHT_WHITE

# This string represents a single level of indentation in the script output in your terminal emulator.
prompt_theme.indent_string = '  '

#---------------------
# Create Build Context

# Create context and configure default paths
CTX = BuildContext(Path().resolve(__file__))

# Store prompt theme
CTX.printer = Printer(prompt_theme)

# ------------------------
# Handle command line args

argument_parser = argparse.ArgumentParser(description="Builds all native libraries, packages plug-ins, and moves packages to build folder.")
argument_parser.add_argument("-p", "--plugin-list", dest="plugin_list", nargs='*', default=[PluginID.ALL], help=f"Selects the plug-ins to process. Possible values are: {PluginID.ACCESSIBILITY}, {PluginID.CORE}, {PluginID.CORE_HAPTICS}, {PluginID.GAME_CONTROLLER}, {PluginID.GAME_KIT}, {PluginID.PHASE}, or {PluginID.ALL}. Default is: {PluginID.ALL}")
argument_parser.add_argument("-m", "--platforms", dest="platform_list", nargs='*', default=[PlatformID.ALL], help=f"Selects the desired platforms to target when building native libraries. Possible values are: {PlatformID.IOS}, {PlatformID.MACOS}, {PlatformID.TVOS}, or {PlatformID.ALL}. Default is: {PlatformID.ALL}")
argument_parser.add_argument("-b", "--build-action", dest="build_actions", nargs='*', default=[BuildActionID.BUILD, BuildActionID.PACK], help=f"Sets the build actions for the selected plug-ins. Possible values are: {BuildActionID.BUILD}, {BuildActionID.PACK}, {BuildActionID.NONE} or {BuildActionID.ALL}. Defaults are: {BuildActionID.BUILD}, {BuildActionID.PACK}")
argument_parser.add_argument("-s", "--simulator-build", dest="simulator_build", action="store_true", help=f"Builds simulator-compatible libraries for supported platforms.")
argument_parser.add_argument("-c", "--codesign-identity", dest="codesign_identity", default=str(), help=f"String which uniquely identifies your codesign identity, typically represented by a hash. Only applied if build actions include {BuildActionID.BUILD}")
argument_parser.add_argument("-sc", "--skip-codesign", dest="skip_codesign", action="store_true", help=f"Skips codesign and all user prompts.")
argument_parser.add_argument("-u", "--unity-installation-root", dest="unity_installation_root", default=CTX.unity_install_root, help="Root path to search for Unity installations. Note: performs a full recursive search of the given directory.")
argument_parser.add_argument("-d", "--debug", dest="debug", action="store_true", help=f"Compiles debug native libraries for the selected plug-ins.")
argument_parser.add_argument("-o", "--output-path", dest="output_path", default=CTX.build_output_path, help=f"Build result path for final packages. Default: {CTX.build_output_path}")
argument_parser.add_argument("-k", "--clean-action", dest="clean_actions", nargs='*', default=[CleanActionID.NONE], help=f"Sets the clean actions for the selected plug-ins. Possible values are: {CleanActionID.NATIVE}, {CleanActionID.PACKAGES}, {CleanActionID.TESTS}, {CleanActionID.NONE}, or {CleanActionID.ALL}. Defaults to no clean action.")
argument_parser.add_argument("-f", "--force", dest="force_clean", action="store_true", help="Setting this option will not prompt user on file deletion during clean operations.")
argument_parser.add_argument("-t", "--test", dest="build_tests", action="store_true", help="Builds Unity tests for each plug-in.")
argument_parser.add_argument("-to", "--test-output-path", dest="test_output_path", default=CTX.test_build_root, help=f"Output path for test build results. Default: {CTX.test_build_root}")

build_args = argument_parser.parse_args()

def Main():
    # Store the time of invocation for later use
    invocation_time = datetime.now()
    invocation_time_string = invocation_time.strftime("%Y-%m-%d_%H-%M-%S")

    print(f"\n{Printer.Bold('*'*80)}"
          f"\n\n{Printer.Bold('Unity Plug-In Build Script'):^80s}"
          f"\n\n{CTX.printer.Context(build_script_version):^80}"
          f"\n\n{Printer.Bold('*'*80)}")
    
    CTX.printer.SectionHeading("Command Line Option Summary")
    
    print(f"\n            Build Actions({Printer.Bold('-b')}): {CTX.printer.Context(' '.join(build_args.build_actions))}"
          f"\n       Selected Platforms({Printer.Bold('-m')}): {CTX.printer.Context(' '.join(build_args.platform_list))}"
          f"\n             Build Config({Printer.Bold('-d')}): {CTX.printer.Context('Debug (-d set)' if build_args.debug else 'Release (-d not set)')}"
          f"\n          Simulator Build({Printer.Bold('-s')}): {CTX.printer.Context('Simulator Build (-s set)' if build_args.simulator_build else 'Standard Build (-s not set)')}"
          f"\n      Package Output Path({Printer.Bold('-o')}): {CTX.printer.Context(build_args.output_path)}"
          f"\n        Selected Plug-Ins({Printer.Bold('-p')}): {CTX.printer.Context(' '.join(build_args.plugin_list))}"
          f"\n            Clean Actions({Printer.Bold('-k')}): {CTX.printer.Context(' '.join(build_args.clean_actions))}"
          f"\n              Force Clean({Printer.Bold('-f')}): {CTX.printer.Context('Yes (-f set)' if build_args.force_clean else 'No (-f not set)')}"
          f"\n  Unity Installation Root({Printer.Bold('-u')}): {CTX.printer.Context(build_args.unity_installation_root)}"
          f"\n              Build Tests({Printer.Bold('-t')}): {CTX.printer.Context('Yes (-t set)' if build_args.build_tests else 'No (-t not set)')}"
          f"\n           Skip Codesign({Printer.Bold('-sc')}): {CTX.printer.Context('Yes (-sc set)' if build_args.skip_codesign else 'No (-sc not set)')}")
    
    if not build_args.skip_codesign:
        print(f"     Codesigning Identity({Printer.Bold('-c')}): {CTX.printer.Context(build_args.codesign_identity if len(build_args.codesign_identity) > 0 else 'None supplied; user will be prompted.')}")

    if build_args.build_tests:
        print(f"        Test Output Path({Printer.Bold('-to')}): {CTX.printer.Context(build_args.test_output_path)}")

    CTX.printer.SectionHeading("Validate Input")

    # -------------------------------------------------------------------------

    CTX.build_actions = {
        BuildActionID.BUILD: False,
        BuildActionID.PACK: False,
    }

    valid_build_action_found = False
    for action in build_args.build_actions:
        if action in CTX.build_actions:
            CTX.build_actions[action] = True
            valid_build_action_found = True
        elif action == BuildActionID.ALL:
            for build_action_key in CTX.build_actions.keys():
                CTX.build_actions[build_action_key] = True
            valid_build_action_found = True
            break
        elif action == BuildActionID.NONE:
            for build_action_key in CTX.build_actions.keys():
                CTX.build_actions[build_action_key] = False
            valid_build_action_found = True
            break
        else:
            CTX.printer.WarningMessage(f"Ignoring unknown build action '{action}'. Valid options are {BuildActionID.BUILD}, {BuildActionID.PACK}, {BuildActionID.ALL} (Default), or {BuildActionID.NONE}")
    
    if not valid_build_action_found:
        CTX.printer.WarningMessage(f"No valid build action passed to build script. Using default argument: {BuildActionID.ALL}")
        for build_action_key in CTX.build_actions.keys():
            CTX.build_actions[build_action_key] = True

    # -------------------------------------------------------------------------

    CTX.platforms = {
        PlatformID.IOS: False,
        PlatformID.MACOS: False,
        PlatformID.TVOS: False
    }

    valid_platform_found = False
    for platform_id in build_args.platform_list:
        if platform_id == PlatformID.ALL:
            valid_platform_found = True
            for selected_platform_key in CTX.platforms.keys():
                CTX.platforms[selected_platform_key] = True
            break
        elif platform_id in CTX.platforms:
            valid_platform_found = True  
            CTX.platforms[platform_id] = True
        else:
            CTX.printer.WarningMessage(f"Ignoring unknown platform '{platform_id}'. Valid options are {PlatformID.IOS}, {PlatformID.MACOS}, {PlatformID.TVOS}, or {PlatformID.ALL} (Default)")

    if not valid_platform_found:
        CTX.printer.WarningMessage(f"No valid platform passed to build script. Using default argument: {PlatformID.ALL}")
        for selected_platform_key in CTX.platforms.keys():
            CTX.platforms[selected_platform_key] = True

    CTX.simulator_build = build_args.simulator_build

    # -------------------------------------------------------------------------

    CTX.plugins = {
        PluginID.ACCESSIBILITY: False,
        PluginID.CORE: False,
        PluginID.CORE_HAPTICS: False,
        PluginID.GAME_CONTROLLER: False,
        PluginID.GAME_KIT: False,
        PluginID.PHASE: False
    }

    valid_plugin_found = False
    for plugin_id in build_args.plugin_list:
        if plugin_id in CTX.plugins:
            CTX.plugins[plugin_id] = True
            valid_plugin_found = True
        elif plugin_id == PluginID.ALL:
            for selected_plugin_key in CTX.plugins.keys():
                CTX.plugins[selected_plugin_key] = True
            valid_plugin_found = True
            break
        else:
            utility.WarningMessage(f"Ignoring unknown plug-in '{plugin_id}'. Valid options are {PluginID.ACCESSIBILITY}, {PluginID.CORE}, {PluginID.CORE_HAPTICS}, {PluginID.GAME_CONTROLLER}, {PluginID.GAME_KIT}, {PluginID.PHASE}, or {PluginID.ALL} (Default)")

    # -------------------------------------------------------------------------

    CTX.build_tests = build_args.build_tests

    # If user has opted to build tests, Apple.Core must also be selected as all plug-ins are dependent upon Apple.Core
    if CTX.build_tests and not CTX.plugins[PluginID.CORE]:
        CTX.printer.WarningMessage(f"Build Tests({Printer.Bold('-t')}) set to true, but Apple.Core has not been selected to process.")
        CTX.printer.InfoMessage("All plug-ins are dependent upon Apple.Core, so it must be built for tests build successfully.")
        CTX.printer.StatusMessage("Adding Apple.Core to selected plug-ins.", "\n")
        CTX.plugins[PluginID.CORE] = True

    if not valid_plugin_found:
        CTX.printer.WarningMessage(f"No valid plug-in passed to build script. Using default argument: {PluginID.ALL}")
        for selected_plugin_key in CTX.plugins.keys():
            CTX.plugins[selected_plugin_key] = True

    # -------------------------------------------------------------------------

    CTX.clean_actions = {
        CleanActionID.NATIVE: False,
        CleanActionID.PACKAGES: False,
        CleanActionID.TESTS: False
    }

    valid_clean_action_found = False
    for action in build_args.clean_actions:
        if action in CTX.clean_actions:
            CTX.clean_actions[action] = True
            valid_clean_action_found = True
        elif action == CleanActionID.ALL:
            for clean_action_key in CTX.clean_actions.keys():
                CTX.clean_actions[clean_action_key] = True
            valid_clean_action_found = True
            break
        elif action == CleanActionID.NONE:
            for clean_action_key in CTX.clean_actions.keys():
                CTX.clean_actions[clean_action_key] = False
            valid_clean_action_found = True
            break
        else:
            CTX.printer.WarningMessage(f"Ignoring unknown clean action '{action}'. Valid options are {CleanActionID.NATIVE}, {CleanActionID.PACKAGES}, {CleanActionID.TESTS}, {CleanActionID.ALL}, or {CleanActionID.NONE} (Default)")

    if not valid_clean_action_found:
        CTX.printer.WarningMessage(f"No valid clean action passed to build script. Using default argument: {CleanActionID.NONE}")
        for clean_action_key in CTX.clean_actions.keys():
            CTX.clean_actions[clean_action_key] = False

    # -------------------------------------------------------------------------

    unity_install_root = Path(build_args.unity_installation_root)
    if unity_install_root.is_dir():
        CTX.unity_install_root = unity_install_root

    # -------------------------------------------------------------------------

    CTX.printer.SectionHeading("Configure Build Paths")

    # Configure build paths for packages
    CTX.build_path = pathlib.Path(build_args.output_path)

    if CTX.clean_actions[CleanActionID.PACKAGES] and CTX.build_path.exists():
        CTX.printer.StatusMessage("Cleaning packages.", "\n")
        CTX.printer.StatusMessageWithContext("Removing folder at path:",  f"{CTX.build_path}")
        utility.RemoveFolder(CTX.build_path, prompt= not build_args.force_clean, printer= CTX.printer)

    if CTX.build_actions[BuildActionID.BUILD] or CTX.build_actions[BuildActionID.PACK]:
        if not CTX.build_path.exists():
            CTX.printer.Message(f"Build output path not found.", "\n")
            CTX.printer.StatusMessageWithContext("Creating: ", f"{CTX.build_path}")
            CTX.build_path.mkdir()

    # Configure and optionally clean paths for test builds
    test_build_root_path = pathlib.Path(build_args.test_output_path)
    if CTX.clean_actions[CleanActionID.TESTS] and test_build_root_path.exists():
        CTX.printer.StatusMessage(f"Clean tests option '{CleanActionID.TESTS}' set.", "\n")
        utility.RemoveFolder(test_build_root_path, prompt= not build_args.force_clean, printer= CTX.printer)
        for curr_plugin_path in CTX.plugin_root.iterdir():
            if not curr_plugin_path.is_dir():
                continue

            # As a standard, all plug-in Unity projects are the name of the plug-in folder with the string '_Unity' appended
            curr_unity_project_path = curr_plugin_path.joinpath(f"{curr_plugin_path.name}_Unity")
            curr_test_player_path = curr_unity_project_path.joinpath("TestPlayers")

            if curr_unity_project_path.is_dir() and curr_test_player_path.is_dir():
                utility.RemoveFolder(curr_test_player_path, prompt= not build_args.force_clean, printer= CTX.printer)

    if CTX.build_tests:
        if not CTX.test_build_root.exists():
            CTX.printer.StatusMessage("Test build output root not found.", "\n")
            CTX.printer.StatusMessageWithContext("Creating: ", f"{CTX.test_build_root}")
            test_build_root_path.mkdir()

        # Each set of test builds for an invocation will store output in a newly time-stamped folder
        CTX.test_build_output_path = CTX.test_build_root.joinpath(f"TestBuild_{invocation_time_string}")
        CTX.test_build_output_path.mkdir()

    # -------------------------------------------------------------------------

    if CTX.build_actions[BuildActionID.BUILD]:
        CTX.printer.SectionHeading("Configure Native Library Build Options")

        xcode_version, xcode_build_number = toolchain.GetToolchainVersions()
        CTX.printer.MessageWithContext("Native library build using: ", f"Xcode {xcode_version} ({xcode_build_number})", "\n")
        CTX.printer.InfoMessage(f"If this is incorrect, please update your environment with {Printer.Bold('xcode-select')}. (Call \'{Printer.Bold('xcode-select -h')}\' from the command line for more info.)")

        CTX.build_config = ConfigID.DEBUG if build_args.debug else ConfigID.RELEASE

        if build_args.skip_codesign:
            CTX.codesign_hash = ""
        else:
            CTX.codesign_hash = build_args.codesign_identity if len(build_args.codesign_identity) > 0 else toolchain.PromptForCodesignIdentity(CTX.printer)

        CTX.printer.SectionHeading("Gather Unity Installation Info")

        unity_plugin_manager = plugin_manager.NativeUnityPluginManager(CTX)
        unity_plugin_manager.ScanForUnityInstallations()

        CTX.printer.SectionHeading("Process Plug-Ins")

        # Sort plug-in build order so that Apple.Core always comes first
        plugin_path_list = list()
        for curr_plugin_path in CTX.plugin_root.iterdir():
            if not curr_plugin_path.is_dir():
                continue

            if curr_plugin_path.name == "Apple.Core":
                plugin_path_list.insert(0, curr_plugin_path)
            else:
                plugin_path_list.append(curr_plugin_path)

        for plugin_path in plugin_path_list:
            unity_plugin_manager.ProcessNativeUnityPlugin(plugin_path)

        CTX.printer.SectionHeading("Update and Create Unity .meta Files")
        unity_plugin_manager.ValidateProjectVersions()

    if CTX.build_tests:
        CTX.printer.SectionHeading("Build Unity Tests")
        unity_plugin_manager.BuildTests()

    if CTX.build_actions[BuildActionID.PACK]:
        CTX.printer.SectionHeading("Create Plug-In Packages")
        unity_plugin_manager.GeneratePlugInPackages()

    CTX.printer.Message("Finished running Unity plug-in build script.", "\n")

# Entry point
if __name__ == '__main__':
    Main()
