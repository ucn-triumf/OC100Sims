# Configure this document to properly set paths for everything

# KEEP THIS IN THE SAME DIRECTORY AS THE OTHER SCRIPTS

# You should configure accounts yourself
# For examples you may want to include this in your .bashrc
# #export SLURM_ACCOUNT=def-rpicker
# #export SBATCH_ACCOUNT=$SLURM_ACCOUNT
# #export SALLOC_ACCOUNT=$SLURM_ACCOUNT

# Your folder structure should be:
# Analysis is the root directory of your Case folders. You may have several cases you are examining inside.
# A Case represents a configuration of the assembly
# A Case is broken up into stages, as few as 1 or as many as 5

# This folder contains your cases and is the root of the analysis
ANALYSIS_PATH=$SCRATCH/OC100/
# Job submissions will be recorded in batchLog.txt in this directory
BATCH_LOG_PATH=$SCRATCH/OC100/
# Where you want your output to go. Should be in your scratch directory usually. Will be organized into the Case folder and then Stage folder will have the output
PENTRACK_OUTPUT_PATH=$SCRATCH/OC100/
# Path to the PENTrack installation, should end in the folder PENTrack
PENTRACK_PATH=$SCRATCH/PENTrack/

# !!!!!!!!!!!!!!!!!!!!!!
# !!! READ CAREFULLY !!!
# !!!!!!!!!!!!!!!!!!!!!!
# Below is the Slurm output configuration. However currently additional parameters are passed to the sbatch command in submitTasks.sh, 
# meaning the --output and --error settings in BATCH_SETTINGS are being overridden. The hardcoded settings in submitTasks.sh output Slurm
# output and error to the same folder as the PENTrack output.

# System slurm output path
#SLURM_OUTPUT_PATH=$SCRATCH/slurmOutput/
# The actual path and filename for the output
#SLURM_OUTPUT_NAME=${SLURM_OUTPUT_PATH}Array_test.%A_%a.out
# System slurm error path, should be different from the output path
#SLURM_ERRORS_PATH=$SCRATCH/slurmErrors/
# The actual path and filename for the errors
#SLURM_ERRORS_NAME=${SLURM_ERRORS_PATH}Array_test.%A_%a.out

# PENTrack batch files will be generated with these settings
BATCH_SETTINGS="
#SBATCH --mem=2200M
#SBATCH --array=1-50
#SBATCH --output=${SLURM_OUTPUT_NAME}
#SBATCH --error=${SLURM_ERRORS_NAME}
#PBS -l walltime=8:00:00
#SBATCH --account=rrg-rpicker
"

