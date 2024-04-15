#!/bin/bash
# Import configuration file
dir=$(dirname "$0")
. ${dir}/config.sh

# Double check before submitting
echo -e "The current analysis folder path in the script is \e[31m${PENTRACK_OUTPUT_PATH}\e[0m "
read -p 'Is this correct? (y/n): '
if [ "$REPLY" != "y" ]
then
	echo -e "\e[31mPlease edit the config script to contain the correct path.\e[0m"
	exit 1
fi

for case_path in ${PENTRACK_OUTPUT_PATH}*/
do
	echo -e "Currently looking at \e[31m${case_path}\e[0m "
	read -p 'Do you want to look at the tasks in here? (y/n): '

	if [ "$REPLY" != "y" ]
	then
		echo -e "\e[31mCase skipped... Moving onto next case.\e[0m"
		continue
	fi

	for stage_path in ${case_path}*/ 
	do		
		# Ask before submitting
		echo -e "We are looking at \e[31m${stage_path}\e[0m "
		read -p 'Do you want to process this? (y/n): '
		if [ "$REPLY" != "y" ]
		then
			echo -e "\e[31mTask skipped... Moving onto next task.\e[0m"
			continue
		fi

		answered="false"
		until [ "$answered" = "true" ]
		do
			read -p 'Is this an emptying, storing, or filling stage? (e/s/f): '
			if [ "$REPLY" = "e" ]
			then
				answered="true"
			elif [ "$REPLY" = "s" ]
			then
				answered="true"
			elif [ "$REPLY" = "f" ]
			then
				answered="true"
			else
				echo "Not a valid choice, try again"
			fi
		done

		# Obtain last two directories in case path, representing stage and case folders
		case_name=$(basename "$case_path")
 		stage_name=$(basename "$stage_path")

 		# The original out.root files are left untouched.
		if [ "$REPLY" = "e" ]
		then
			echo "read e"
			python cellEmpty.py ${stage_path}*.root
			# move the file to target directory rename it
			mv "${stage_path}out_DetEff.root" "${ANALYSIS_PATH}${case_name}/${stage_name}.root"
		elif [ "$REPLY" = "s" ]
		then
			echo "read s"
			python cellStorage.py ${stage_path}*.root
			# move the file to target directory rename it
			mv "${stage_path}out_hist.root" "${ANALYSIS_PATH}${case_name}/${stage_name}.root"
		elif [ "$REPLY" = "f" ]
		then
			echo "read f"
			# move the file to target directory rename it
			python cellFill.py ${stage_path}*.root
			mv "${stage_path}out_fill.root" "${ANALYSIS_PATH}${case_name}/${stage_name}.root"
		fi
	done
done

