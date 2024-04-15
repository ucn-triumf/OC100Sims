#!/bin/sh

#SBATCH --mem=2200M
#SBATCH --array=1-50
#PBS -l walltime=4:00:00
###SBATCH --account=rrg-rpicker


ID=$SLURM_ARRAY_TASK_ID
JOB=$SLURM_ARRAY_JOB_ID

$SCRATCH/PENTrack/PENTrack $JOB$ID $SCRATCH/OC100/PENTrack/bottomStorage/config.in $SCRATCH/OC100/results/bottomStorage/
