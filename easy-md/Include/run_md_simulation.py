#!/usr/bin/env python3
"""
External script for running molecular dynamics simulations with easy_md.
This script is called by the HorusAPI plugin using subprocess and conda run.
"""

import json
import sys
import os
import glob
from easy_md.utils.config import create_config
from easy_md.main import (
    run_solvation,
    run_forcefield_parameterization,
    run_energy_minimization,
    run_simulation,
)


def main():
    if len(sys.argv) != 2:
        print("Usage: python run_md_simulation.py <params_json_file>")
        sys.exit(1)

    params_file = sys.argv[1]

    try:
        # Load parameters from JSON file
        with open(params_file, "r") as f:
            params = json.load(f)

        print("MD Simulation Script Started")
        print("=" * 50)
        print(f"Parameters loaded from: {params_file}")
        print(f"Protein file: {params['protein_file']}")
        print(f"Ligand file: {params['ligand_file']}")
        print(f"MD steps: {params['md_steps']}")
        print(f"Save interval: {params['md_save_interval']}")
        print(f"Platform: {params['platform_name']}")
        print(f"Precision: {params['platform_precision']}")
        if params["starting_state_path"]:
            print(f"Starting state: {params['starting_state_path']}")
        print("=" * 50)

        # Validate input files exist
        if not os.path.exists(params["protein_file"]):
            raise FileNotFoundError(f"Protein file not found: {params['protein_file']}")
        if not os.path.exists(params["ligand_file"]):
            raise FileNotFoundError(f"Ligand file not found: {params['ligand_file']}")
        if params["starting_state_path"] and not os.path.exists(
            params["starting_state_path"]
        ):
            raise FileNotFoundError(
                f"Starting state file not found: {params['starting_state_path']}"
            )

        # Create configuration
        print("Step 1: Creating configuration...")
        config = create_config(
            protein_file=params["protein_file"],
            ligand_file=params["ligand_file"],
            md_steps=params["md_steps"],
            md_save_interval=params["md_save_interval"],
            platform_name=params["platform_name"],
            platform_precision=params["platform_precision"],
        )
        print("✓ Configuration created successfully")

        # Run solvation
        print("\nStep 2: Adding water (solvation)...")
        run_solvation.add_water(config=config)
        print("✓ Solvation completed successfully")

        # Run force field parameterization
        print("\nStep 3: Running force field parameterization...")
        run_forcefield_parameterization.main(config)
        print("✓ Force field parameterization completed successfully")

        # Run energy minimization
        print("\nStep 4: Running energy minimization...")
        run_energy_minimization.main(config)
        print("✓ Energy minimization completed successfully")

        # Run simulation
        print("\nStep 5: Running MD simulation...")
        if params["starting_state_path"]:
            run_simulation.main(
                config, starting_state_path=params["starting_state_path"]
            )
            print(
                f"✓ Simulation completed successfully with initial state: {params['starting_state_path']}"
            )
        else:
            run_simulation.main(config)
            print("✓ Simulation completed successfully from minimized structure")

        # Get output file paths from the expected locations
        # Topology file is in output/emin.pdb
        topology_file = os.path.abspath("output/emin.pdb")

        # Trajectory file is in output/md_trajectory_id_0.dcd # TODO: TYPO HERE! traJetory
        trajectory_file = os.path.abspath("output/md_trajetory_id_0.dcd")

        # Verify the files exist
        if not os.path.exists(topology_file):
            print(f"Warning: Expected topology file not found at {topology_file}")
            # Try alternative locations
            alt_topo_files = [
                "output/emin.pdb",
                "emin.pdb",
                "output/system.pdb",
                "system.pdb",
            ]
            topology_file = ""
            for alt_file in alt_topo_files:
                if os.path.exists(alt_file):
                    topology_file = os.path.abspath(alt_file)
                    print(f"Found topology file at: {topology_file}")
                    break

        if not os.path.exists(trajectory_file):
            print(f"Warning: Expected trajectory file not found at {trajectory_file}")
            # Try alternative locations and patterns
            import glob

            traj_patterns = [
                "output/md_trajectory_id_*.dcd",
                "output/md_trajectory*.dcd",
                "output/trajectory*.dcd",
                "md_trajectory_id_*.dcd",
                "trajectory.dcd",
            ]
            trajectory_file = ""
            for pattern in traj_patterns:
                matches = glob.glob(pattern)
                if matches:
                    trajectory_file = os.path.abspath(
                        matches[0]
                    )  # Take the first match
                    print(f"Found trajectory file at: {trajectory_file}")
                    break

        print("\n" + "=" * 50)
        print("MD SIMULATION SETUP COMPLETED SUCCESSFULLY!")
        print("=" * 50)

        # Output file paths for the plugin to parse
        if topology_file and os.path.exists(topology_file):
            print(f"TOPOLOGY_FILE:{topology_file}")
        else:
            print("TOPOLOGY_FILE:Not found - expected at output/emin.pdb")

        if trajectory_file and os.path.exists(trajectory_file):
            print(f"TRAJECTORY_FILE:{trajectory_file}")
        else:
            print(
                "TRAJECTORY_FILE:Not found - expected at output/md_trajectory_id_0.dcd"
            )

    except FileNotFoundError as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR during MD simulation: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
