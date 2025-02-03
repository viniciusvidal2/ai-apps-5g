# ai-apps-5g
This repository will hold the codes for the AI apps we build in the 5G context

## Reproducing the AI tools with conda environment
This instructions should run on a linux machine with a proper NVidia GPU installed. The actual test ran on a laptop i7 12th generation, 3050 RTX GPU.

To install Anaconda, follow the instructions in the [official website](https://www.anaconda.com/download). You should end up with a base environment in your terminal.

To create our environment to run the code in this repo, use the file ai_environment.yml and call the following command:

```bash
cd /path/to/this/repo
conda env create --file=ai_environment.yml
```

Cuda and tensorflow versions might need to adapt, but you should be able to run the example scripts after successful installation.

## Sample data
The audio file we are using as an example can be downloaded from [this google drive link](https://drive.google.com/file/d/1Y_76o_JHO1fKb_lL-e-7G7UnnCcN1Ea6/view?usp=drive_link)
