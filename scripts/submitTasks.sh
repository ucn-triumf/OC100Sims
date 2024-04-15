# Submits user requested tasks in the Case directory to SLURM for processing
# Maintains record of tasks in the case folder
# Last updated April 9, 2020, by Sean Lan

# Import configuration file to load paths
dir=$(dirname "$0")
. ${dir}/config.sh

# Get date and store so it can be used for the text file later
now=$(date +'%Y-%m-%d|%T')

# Double check that the configuration is correct before proceeding
echo -e "The current analysis folder path in the script is \e[31m${ANALYSIS_PATH}\e[0m "
read -p 'Is this correct? (y/n): '
if [ "$REPLY" != "y" ]
then
	echo -e "\e[31mPlease edit the config script to contain the correct path.\e[0m"
	exit 1
fi

# Ask if the user wants to automatically add a merge job to slurm. If not, merge must be manually submitted separately.
merge="false"
read -p 'Would you like to automatically merge outputs after tasks are completed? (y/n): '
if [ "$REPLY" = "y" ]
then
	merge="true"
fi

# Start going down the folder directory and asking if the user wants to enter each case folder
for case_path in ${ANALYSIS_PATH}*/
do
	echo -e "Currently looking at \e[31m${case_path}\e[0m "
	read -p 'Do you want to look at the tasks in here? (y/n): '

	# If not, move onto the next case
	if [ "$REPLY" != "y" ]
	then
		echo -e "\e[31mCase skipped... Moving onto next case.\e[0m"
		continue
	fi

	# Start going down the case directory and ask if the user wants to enter each stage folder
	for stage_path in ${case_path}*/ 
	do

		# Ask before submitting
		echo -e "Currently submitting task in \e[31m${stage_path}\e[0m "
		read -p 'Do you want to submit this?? (y/n): '
		if [ "$REPLY" != "y" ]
		then
			echo -e "\e[31mTask skipped... Moving onto next task.\e[0m"
			continue
		fi

 		# Obtain last two directories in case path, representing stage and case folders
		case_name=$(basename "$case_path")
 		stage_name=$(basename "$stage_path")
		D2=$(dirname "$stage_path")
		D3=$(basename "$D2")/$(basename "$stage_path")

		# Submit job and record id with --parsable tag
		job_id=$(sbatch --parsable --output=${PENTRACK_OUTPUT_PATH}${case_name}/${stage_name}/%A_%a.slurmoutput ${stage_path}batch.sh)

 		if [ "$merge" = "true" ]
 		then
 			# Submit merge task
 			merge_job_id=$(sbatch --output=${PENTRACK_OUTPUT_PATH}${case_name}/${stage_name}/%A.slurmoutput --parsable --dependency=afterany:$job_id ${stage_path}postprocess.sh $job_id)

 			# Log submission
 			echo "Submitted task ${job_id} and merge task ${merge_job_id} at ${now} for ${D3}" >> ${BATCH_LOG_PATH}/batchLog.txt
 		else
 			# Log submission
 			echo "Submitted task ${job_id} at ${now} for ${case_name}/${stage_name}/" >> ${BATCH_LOG_PATH}/batchLog.txt
 		fi
	done
done

echo "Tasks submitted"
