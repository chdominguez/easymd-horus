from HorusAPI import PluginVariable, PluginBlock, VariableTypes
import subprocess
import json
import os
import tempfile

# Input variables
proteinFile = PluginVariable(
    name="Protein File",
    id="protein_file",
    description="Path to the protein PDB file.",
    type=VariableTypes.FILE,
)

ligandFile = PluginVariable(
    name="Ligand File",
    id="ligand_file",
    description="Path to the ligand SDF file.",
    type=VariableTypes.FILE,
)

# MD simulation settings variables
mdSteps = PluginVariable(
    name="MD Steps",
    id="md_steps",
    description="Number of molecular dynamics simulation steps.",
    type=VariableTypes.INTEGER,
    defaultValue=1000,
)

mdSaveInterval = PluginVariable(
    name="MD Save Interval",
    id="md_save_interval",
    description="Interval for saving simulation frames.",
    type=VariableTypes.INTEGER,
    defaultValue=10,
)

# Platform settings variables
platformName = PluginVariable(
    name="Platform Name",
    id="platform_name",
    description="Computing platform to use (CPU or GPU).",
    type=VariableTypes.STRING_LIST,
    defaultValue="CPU",
    allowedValues=["CPU", "GPU"],
)

platformPrecision = PluginVariable(
    name="Platform Precision",
    id="platform_precision",
    description="Numerical precision for calculations (mixed, single, or double).",
    type=VariableTypes.STRING_LIST,
    defaultValue="mixed",
    allowedValues=["mixed", "single", "double"],
)

# Optional starting state
startingStatePath = PluginVariable(
    name="Starting State Path",
    id="starting_state_path",
    description="Optional path to starting state XML file for simulation.",
    type=VariableTypes.FILE,
    allowedValues=["xml"],
)

# Conda environment variable
condaEnv = PluginVariable(
    name="Conda Environment",
    id="conda_env",
    description="Name of the conda environment containing easy_md.",
    type=VariableTypes.STRING,
    defaultValue="easymd",
)

# Output variables
topologyOutput = PluginVariable(
    name="Topology File",
    id="topology_output",
    description="Path to the generated topology file (.pdb or .prmtop).",
    type=VariableTypes.FILE,
    allowedValues=["*"],
)

trajectoryOutput = PluginVariable(
    name="Trajectory File",
    id="trajectory_output",
    description="Path to the generated trajectory file (.dcd or .nc).",
    type=VariableTypes.FILE,
    allowedValues=["*"],
)


# Main function to run the MD simulation setup
def runMDSimulation(block: PluginBlock):
    # Get input values
    protein_path = block.inputs.get("protein_file", None)
    ligand_path = block.inputs.get("ligand_file", None)

    if protein_path is None:
        raise Exception("Protein file path is required.")
    if ligand_path is None:
        raise Exception("Ligand file path is required.")

    # Get simulation parameters
    md_steps = block.variables.get("md_steps", 1000)
    md_save_interval = block.variables.get("md_save_interval", 10)
    platform_name = block.variables.get("platform_name", "CPU")
    platform_precision = block.variables.get("platform_precision", "mixed")
    starting_state_path = block.variables.get("starting_state_path", "")
    conda_env = block.variables.get("conda_env", "easymd")

    # Create parameter dictionary for the external script
    params = {
        "protein_file": protein_path,
        "ligand_file": ligand_path,
        "md_steps": md_steps,
        "md_save_interval": md_save_interval,
        "platform_name": platform_name,
        "platform_precision": platform_precision,
        "starting_state_path": starting_state_path,
    }

    try:
        # Create temporary file for parameters
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as param_file:
            json.dump(params, param_file, indent=2)
            param_file_path = param_file.name

        print(f"Created configuration for protein: {protein_path}")
        print(f"Ligand: {ligand_path}")
        print(f"MD Steps: {md_steps}, Save Interval: {md_save_interval}")
        print(f"Platform: {platform_name}, Precision: {platform_precision}")
        print(f"Using conda environment: {conda_env}")

        # Get the directory where this plugin file is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, "run_md_simulation.py")

        # Run the external script using conda run
        cmd = [
            "/opt/homebrew/bin/micromamba",
            "run",
            "-n",
            conda_env,
            "python",
            "-u",
            script_path,
            param_file_path,
        ]

        print("Starting MD simulation...")
        print(f"Command: {' '.join(cmd)}")

        # Parse the output to get file paths
        topology_file = ""
        trajectory_file = ""

        # Execute the command
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stderr with stdout
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True,
        ) as p:

            # Stream output line by line
            for line in p.stdout:
                line = line.rstrip()
                print(line)

                # Parse output file paths as they come
                if line.startswith("TOPOLOGY_FILE:"):
                    topology_file = line.split(":", 1)[1].strip()
                elif line.startswith("TRAJECTORY_FILE:"):
                    trajectory_file = line.split(":", 1)[1].strip()

            # Wait for process to complete and get return code
            return_code = p.wait()

            if return_code != 0:
                raise subprocess.CalledProcessError(return_code, cmd)

        # Clean up temporary file
        os.unlink(param_file_path)

        # Set outputs
        block.setOutput("topology_output", topology_file)
        block.setOutput("trajectory_output", trajectory_file)

        print(f"MD simulation completed!")
        print(f"Topology file: {topology_file}")
        print(f"Trajectory file: {trajectory_file}")

    except subprocess.CalledProcessError as e:
        error_msg = f"Error running MD simulation script: {str(e)}"
        if e.stderr:
            error_msg += f"\nScript error output: {e.stderr}"
        print(error_msg)
        # Clean up temporary file if it exists
        if "param_file_path" in locals() and os.path.exists(param_file_path):
            os.unlink(param_file_path)
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"Error during MD simulation setup: {str(e)}"
        print(error_msg)
        # Clean up temporary file if it exists
        if "param_file_path" in locals() and os.path.exists(param_file_path):
            os.unlink(param_file_path)
        raise Exception(error_msg)


# Create the plugin block
mdSimulationBlock = PluginBlock(
    name="MD Simulation Setup",
    description="Sets up and runs a complete molecular dynamics simulation including solvation, force field parameterization, energy minimization, and simulation.",
    action=runMDSimulation,
    inputs=[proteinFile, ligandFile],
    variables=[
        mdSteps,
        mdSaveInterval,
        platformName,
        platformPrecision,
        startingStatePath,
        condaEnv,
    ],
    outputs=[topologyOutput, trajectoryOutput],
    id="md_simulation_setup",
    category="Molecular Dynamics",
)
