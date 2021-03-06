import os
import numpy     as np
import pandas    as pd
from tqdm        import tqdm
from glob        import glob

import dirs
import defs

def opposite_number(x, infLim, supLim, k=1.0):
    '''
        Compute opposite number in relation to the n-dimensional real input x.
        Input must be limited to [infLim, supLim] in every dimension.

        Returns x_opposite
    '''
    if k == 'random':
        k = np.random.random(size=(1,1))
        k = np.tile(k, np.shape(x))
    x_opposite = k*(infLim + supLim) - x
    return x_opposite

def make_function_table(data, num_runs, scale='auto'):
    if scale == 'auto':
        scale = list(range(data.shape[0]))
    scale = scale/np.amax(scale)

    errorTable = pd.DataFrame()
    for run in range(0, num_runs):
        index = (data['Run'] == run)

        subTable = pd.DataFrame(data.values[index, :-1])
        generations = subTable.shape[0]

        # Only include a pre-determined set of generations
        fesIndex = (generations - 1)*np.array(scale)
        fesIndex = fesIndex.round().astype(int)

        # Get only the best individuals
        subTable = subTable.min(axis=1, skipna=False)

        # Append Run data to the table
        errorTable['Run {:2d}'.format(run)] = subTable.iloc[fesIndex].values

    # Add a column with each function's mean error over all runs
    errorTable["Mean"] = errorTable.mean(axis=1, skipna=True)

    return errorTable

def make_tables(algorithm, dim, num_runs=50, target_error=1e-8):
    folder = dirs.results+algorithm+"/"
    folderList = glob(folder+"**/", recursive=True)

    # Check if input folder exists
    fileList = glob(folder+"**/*dim"+str(dim)+"*.hdf", recursive=True)
    if (fileList == []):
        print("\nInput: {}\nAlgorithm: {}\nDim: {}\nNot Found".format(folder, algorithm, dim))
        return False
    else:
        ## Table1: Error statistics per function
        # If there are no subfolders, resume process on root folder
        if (folderList == []):
            folderList = [folder]

        # Check for subfolders up to one level to mantain same folder structure on saving
        for subfolder in folderList:
            subfolder = subfolder.replace("\\", "/")
            subFileList = glob(subfolder+"*dim"+str(dim)+"*.hdf")

            print("\nInput: {}\nAlgorithm: {}\nDim: {}\nNum Runs: {}\nTarget Error: {}".format(subfolder, algorithm, dim, num_runs, target_error))
            print("\n------------Table 1 Start----------------")

            errorTable = pd.DataFrame()

            for file in tqdm(subFileList):
                file = file.replace("\\", "/")
                data = load_data(file)

                # Drop filename to get folder structure
                folderStructure = file.split("/")[:-1]
                folderStructure = "/".join(folderStructure)+"/"

                # Append to table best error of each Run
                subTable = data.groupby(by="Run").min().T

                errorTable = errorTable.append(subTable)

            # Count sucessess as error <= target_error
            successTable = np.sum(np.where(errorTable <= target_error, 1, 0), axis=1)/errorTable.shape[1]

            # Compose statistics table
            table1 = pd.DataFrame(data={'Best': errorTable.min(axis=1), 'Worst':errorTable.max(axis=1),
                                        'Median':errorTable.median(axis=1), 'Mean':errorTable.mean(axis=1),
                                        "Std": errorTable.std(axis=1), "Success Rate": successTable})
            # Save as excel file
            if not(table1.empty):
                savePath = folderStructure.replace(dirs.results, dirs.tables)

                # Create folders
                try:
                    os.makedirs(savePath)
                except OSError:
                    pass

                savePath += "{}_table1_dim{}.xlsx".format(algorithm, dim)
                print("Table1 saved at\n{}\n".format(savePath))
                table1.to_excel(savePath, float_format="%.6f", index_label="F#")
            else:
                print("\nERROR: Empty table, skipping save.")

        print("\n------------Table 2 Start----------------")
        ## Table2: Best error evolution per generation per function
        fileList = glob(folder+"**/*dim"+str(dim)+"*.hdf", recursive=True)
        # for file in fileList:
        #     file = file.replace("\\", "/")
        #     print(file)
        # input()
        for file in tqdm(fileList):
            file = file.replace("\\", "/")
            print("\n", file)

            # Get file folder structure for saving
            folderStructure = file.split("/")[:-1]
            folderStructure = "/".join(folderStructure)+"/"

            fileName = file.split("/")[-1]

            data = pd.read_hdf(file)
            errorTable = pd.DataFrame()
            num_runs = data["Run"].max()

            # Get function number and store as Key
            try:
                keyPos = fileName.split("_").index("F")
            except ValueError:
                try:
                    keyPos = fileName.split("_").index("func*")
                except ValueError:
                    print("\nERROR: File \n{}\n doesn't have function indicator.\n".format(fileName))
                    continue

            key = "F"+fileName.split("_")[keyPos+1]
            print("\n", key)

            # For each run, get evolution of best errors per generation
            errorTable = make_function_table(data, num_runs, scale=defs.fesScale)
            errorTable = pd.DataFrame({'MaxFES': defs.fesScale}).set_index('MaxFES')

            # Save as excel file
            if not(errorTable.empty):
                savePath = folderStructure.replace(dirs.results, dirs.tables)

                # Create folders
                try:
                    os.makedirs(savePath)
                except OSError:
                    pass

                savePath += "{}_table2_{}_dim{}.xlsx".format(algorithm, key, dim)
                print(savePath)
                errorTable.to_excel(savePath, float_format="%.8f", index_label='MaxFES')

        return True


def get_solution(func_id=1, dim=10):
    '''
        func_list: Function id, between 1 and 31.
        dim      : Problem dimensionality

        Returns a solution corresponding the global optima of the function given
        by func_id.
    '''
    import pygmo    as pg
    from glob       import glob

    # solution = dict()
    if func_id < 23:
        prob = pg.problem(pg.cec2014(prob_id=func_id, dim=dim))
        shift_data = np.loadtxt(dirs.input+"shift_data_{}.txt".format(func_id))

        # solution[func_id] = prob.fitness(shift_data[:dim])[0]
        solution = prob.fitness(shift_data[:dim])[0]

    if func_id >= 23:
        raise NotImplementedError("f_{:2d} not yet implemented".format(func_id))
        return None
    return solution

def load_data(path):
    #TODO: Make this a generic data-loading script.
    # Currently works only for table1
    import pandas   as pd

    data = pd.read_hdf(path)
    fileName = path.split("/")[-1]

    # Get function number and store as Key
    try:
        keyPos = fileName.split("_").index("F")
    except ValueError:
        try:
            keyPos = fileName.split("_").index("func*")
        except ValueError:
            print("\nERROR: File \n{}\n doesn't have function indicator.\n".format(fileName))
            return False

    key = "F"+fileName.split("_")[keyPos+1]

    # key = "F"+path.split("_")[1][-2:]

    newData = data.drop('Run', axis=1).min(axis=1)
    newData = pd.DataFrame(data={key: newData, 'Run': data['Run']})
    return newData

# def save_to_latex(result1_path, result2_path):
#     import pandas   as pd
#
#     data1 = pd.read_hdf(result1_path)
#     # data2 = pd.read_hdf(result2_path)
#     grouped = data1.groupby(by='Run')
#
#     for group in grouped.groups:
#         print(group)
#
#
#     return data1
