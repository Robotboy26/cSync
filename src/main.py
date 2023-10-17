import tkinter as tk
from tkinter import filedialog
import hashlib
import os
import threading
import concurrent.futures
import sys
import subprocess
import pysftp
import time
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
load_dotenv() # load the .env file

# todo

# create a file that will just update the target sync file on the target computer (ran from that target computer) so that is any files are deleted or anything the file is up to date and will have the correct data

# make it so that it will compress directorys and then send them and then uncompress them once they reach the target

tTimeS = time.time()

def calculate_md5(filePath):
    md5Hash = hashlib.md5()
    with open(filePath, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            md5Hash.update(chunk)
    return md5Hash.hexdigest()

def calculate_sha256(filePath):
    sha256Hash = hashlib.sha256()
    with open(filePath, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256Hash.update(chunk)
    return sha256Hash.hexdigest()

def stringFromEnd(string, stringBase):
    x = len(stringBase) - len(string)
    return string[x:]

def removeFileFromEnd(fileName):
    old = fileName
    y = ""
    x = 0
    while y != "/":
        x = x + 1
        try:
            y = fileName[len(fileName) - x]
            if x > 2000:
                quit("when over the max")
        except:
            return old

    return fileName[:(len(fileName) - (x - 1))]


def selectFolder():
    root = tk.Tk()
    root.withdraw()
    
    folderPath = filedialog.askdirectory(title="Select a Folder")
    
    if folderPath:
        print(f"Selected folder: {folderPath}")
    else:
        print("No folder selected.")

    return folderPath

def getFilesInFolder(folderPath):
    fileList = []
    for root, dirs, files in os.walk(folderPath):
        for file in files:
            filePath = os.path.join(root, file)
            fileList.append(filePath)
    return fileList

def compareFileTime(filePath, timeDict, md5s, sha256s, skippedFiles):
    try:
        t = timeDict[filePath]
        ft = str(getFileTime(filePath))
        if t == ft:
            skippedFiles.append(filePath)
        else:
            md5s.append(f"{filePath}|{calculate_md5(filePath)}")
            sha256s.append(f"{filePath}|{calculate_sha256(filePath)}")
    except:
        md5s.append(f"{filePath}|{calculate_md5(filePath)}")
        sha256s.append(f"{filePath}|{calculate_sha256(filePath)}")

def calculate_md5_sha256(file):
    # Calculate both MD5 and SHA256 checksums for the file
    md5 = calculate_md5(file)
    sha256 = calculate_sha256(file)
    return md5, sha256, file

def mchecksums(files, syncFile, syncCheckFile):
    startTime = time.time()
    noPast = False
    md5s, sha256s = [], []
    timeDict = {}
    fileMdShaDict = {}

    try:
        with open(syncCheckFile, 'r') as checkF:
            fileMdSha = checkF.read().splitlines()
        checkF.close()
    except FileNotFoundError:
        noPast = True
 
    if not noPast:
        for line in fileMdSha:
            file, md, sha = line.split("|")
            fileMdShaDict[file] = f"{md}|{sha}"

    if not noPast:
        with open(syncFile, 'r') as timeFile:
            fileTimeList = timeFile.read().splitlines()
        timeFile.close()
        for line in fileTimeList:
            print(line)
            fileOnly, timeOnly = line.split("|")
            timeDict[fileOnly] = timeOnly

    skippedFiles = []
    print("Checking files... (this might take a while)")

    if not noPast:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for file in files:
                if file in timeDict:
                    if timeDict[file] == str(getFileTime(file)):
                        skippedFiles.append(file)
                    else:
                        futures.append(executor.submit(calculate_md5_sha256, file))
                else:
                    futures.append(executor.submit(calculate_md5_sha256, file))

            for future in concurrent.futures.as_completed(futures):
                md5, sha256, file = future.result()
                md5s.append(f"{file}|{md5}")
                sha256s.append(f"{file}|{sha256}")
    else:
        print("There is no past data. This might take a while.")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(calculate_md5_sha256, file) for file in files]
            for future in concurrent.futures.as_completed(futures):
                md5, sha256, file = future.result()
                md5s.append(f"{file}|{md5}")
                sha256s.append(f"{file}|{sha256}")
    
    newMd5s, newSha256s = [], []
    n = 0
    for file in files:
        try:
            if file in skippedFiles:
                newMd5s.append(fileMdShaDict[file].split("|")[1])
                newSha256s.append(fileMdShaDict[file].split("|")[1])
            else:
                newMd5s.append(md5s[n].split("|")[1])
                newSha256s.append(sha256s[n].split("|")[1])
                n += 1
        except Exception as e:
            print(e)
            try:
                newMd5s.append(md5s[n].split("|")[1])
                newSha256s.append(sha256s[n].split("|")[1])
                n += 1
            except Exception as e:
                newMd5s.append(calculate_md5(file))
                newSha256s.append(calculate_sha256(file))

    endTime = time.time() - startTime
    print(f"It took {endTime}s to check all files. {len(files) - len(skippedFiles)} files needed to be rehashed.")
    return newMd5s, newSha256s

def genCheckFile(files, md5s, sha256s, syncCheckFile):
    checkFileData = []
    for x in range(len(files)):
        file = files[x]
        md5 = md5s[x]
        sha256 = sha256s[x]
        checkFileData.append(f"{file}|{md5}|{sha256}")

    with open(syncCheckFile, 'w') as checkFile:
        checkFile.write("\n".join(checkFileData))
        checkFile.close()

    return checkFileData

def quickCompareCheck(syncCheckFile, targetSyncCheckFile):
    # do a fast check to compare both files
    with open(syncCheckFile, 'r') as localCheck:
        localCheckList = localCheck.read().splitlines()
        localCheck.close()

    with open(targetSyncCheckFile, 'r') as targetCheck:
        targetCheckList = targetCheck.read().splitlines()
        targetCheck.close()

    same = True
    for x in range(len(localCheckList)):
        try:
            if localCheckList[x] == targetCheckList[x]:
                same = True
            else:
                same = False
        except Exception as IndexError:
            same = False

def fullCompareCheck(syncCheckFile, targetSyncCheckFile):
    modifiedFiles, removeFiles = [], []
    with open(syncCheckFile, 'r') as localCheck:
        localCheckList = localCheck.read().splitlines()

    with open(targetSyncCheckFile, 'r') as targetCheck:
        targetCheckList = targetCheck.read().splitlines()

    localCheckListFiles = np.array([line.split("|")[0] for line in localCheckList])
    targetCheckListFiles = np.array([line.split("|")[0] for line in targetCheckList])

    def compareFiles(local, target):
        localFile, localHash, localTime = local.split("|")
        targetFile, targetHash, targetTime = target.split("|")
        if localFile == targetFile and localHash == targetHash and localTime == targetTime:
            return None
        else:
            return localFile

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(compareFiles, localCheckList, targetCheckList)
        modifiedFiles = np.array([file for file in results if file is not None])

    removeFiles = np.setdiff1d(targetCheckListFiles, localCheckListFiles)

    return modifiedFiles.tolist(), removeFiles.tolist()

def getChecksumFile(location, syncCheck, targetSyncCheckFile, USERNAME, TARGET_COMPUTER):
    checksum = subprocess.run(["scp", f"{USERNAME}@{TARGET_COMPUTER}:~/{syncCheck}", f"./{targetSyncCheckFile}"], stdout=subprocess.PIPE) # this will download the checksum file from the target computer 
    print(checksum.stdout) 

def convert_to_dict(file_path):
    data_dict = {}
    if os.path.isfile(file_path):
        with open(file_path, "r") as check:
            checkFileData = check.read().splitlines()
            check.close()
            for line in checkFileData:
                file_data = line.split("|")
                data_dict[file_data[0]] = file_data[1:]
    return data_dict

def scp(files, basePath, USERNAME, PASSWORD, TARGET_COMPUTER, DATALOCATION, targetSyncCheckFile, syncCheck, removeFiles=None):
    if os.path.isfile(f"{DATALOCATION}{syncCheck}"):
        checkFileDict = convert_to_dict(f"{DATALOCATION}{syncCheck}")
    else:
        checkFileDict = None

    if os.path.isfile(f"{targetSyncCheckFile}"):
        targetCheckFileDict = convert_to_dict(targetSyncCheckFile)
    else:
        targetCheckFileDict = None

    with pysftp.Connection(TARGET_COMPUTER, username=USERNAME, private_key='~/.ssh/id_rsa', private_key_pass=f"{PASSWORD}") as sftp:
        with sftp.cd(basePath):
            if removeFiles != None:
                for removeF in removeFiles:
                    removeRelitive = stringFromEnd(removeF, basePath)
                    print(f"removing: {removeRelitive}")
                    try:
                        sftp.remove(removeRelitive)
                    except:
                        print("could not remove")

            for send in files:
                end = stringFromEnd(send, basePath)
                end = removeFileFromEnd(end)
                sendWithout = removeFileFromEnd(send)
                sendRelitive = stringFromEnd(sendWithout, f"{basePath}/")
                if sendRelitive != "/":
                    sendRelitive = sendRelitive[1:]
                print(f"sendRelitive {sendRelitive}")
                print(f"send: {send}")
                print(f"end: {end}")
                send = send.strip("")
                end = end.strip("")
                if sendRelitive != "/":
                    sftp.makedirs(sendRelitive)
                    with sftp.cd(sendRelitive):
                        if checkFileDict and targetCheckFileDict != None:
                            try:
                                if checkFileDict[send] != targetCheckFileDict[send]:
                                    sftp.put(send)
                            except:
                                sftp.put(send)
                        else:
                            sftp.put(send)
                else:
                    if checkFileDict and targetCheckFileDict != None:
                        try:
                            if checkFileDict[send] != targetCheckFileDict[send]:
                                sftp.put(send)
                        except:
                            sftp.put(send)
                    else:
                        sftp.put(send)

def getFileTime(filePath):
    try:
        timestamp = os.path.getmtime(filePath)
        writeTime = datetime.fromtimestamp(timestamp)
        return writeTime
    except FileNotFoundError:
        print(f"File '{filePath}' not found.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def saveLocal(DATALOCATION, syncCheck, checkFileData):
    with open(f"{DATALOCATION}{syncCheck}", 'w') as SyncTargetCheck:
        SyncTargetCheck.write("\n".join(checkFileData))
        SyncTargetCheck.close()

def main():
    TARGET_COMPUTER = os.getenv('TARGET_COMPUTER')
    USERNAME = os.getenv('USERNAME')
    PASSWORD = os.getenv('PASSWORD')
    DATALOCATION = os.getenv('DATALOCATION')
    TARGETLOCATION = os.getenv('TARGETLOCATION')
    syncFile = "data/sync.csync"
    syncCheck = "syncCheck.csync"
    syncCheckFile = "data/syncCheck.csync"
    targetSyncCheckFile = "targetSyncCheck.csync"
    targetPath = "temp"
    if len(sys.argv) > 1:
        folderPath = sys.argv[1]
    else:
        folderPath = selectFolder()
    print(folderPath)
    files = getFilesInFolder(folderPath)
    syncList = []
    for file in files:
        fileTime = getFileTime(file)
        syncList.append(f"{file}|{fileTime}")

    with open(syncFile, "w") as File:
        File.write("\n".join(syncList) + "\n")
        File.close()
        
    md5s, sha256s = mchecksums(files, syncFile, syncCheckFile)
    checkFileData = genCheckFile(files, md5s, sha256s, syncCheckFile)
    saveLocal(DATALOCATION, syncCheck, checkFileData)
    getChecksumFile(f"~/{targetPath}", syncCheck, targetSyncCheckFile, USERNAME, TARGET_COMPUTER)
    if os.path.isfile(targetSyncCheckFile):
        if quickCompareCheck(syncCheckFile, targetSyncCheckFile):
            os.remove(targetSyncCheckFile) # remove the check file gotten from the target computer once it is does being used
            print("You are already synced")
        else:
            modifiedFiles, removeFiles = fullCompareCheck(syncCheckFile, targetSyncCheckFile)
            print("here2")
            scp(modifiedFiles, TARGETLOCATION, USERNAME, PASSWORD, TARGET_COMPUTER, DATALOCATION, targetSyncCheckFile, syncCheck, removeFiles)
            os.remove(targetSyncCheckFile) # remove the check file gotten from the target computer once it is does being used
            print(f"sync took {time.time() - tTimeS}")
            print("synced all files")
    else:
        # if this is the case that assume that it has never synced before and zip the containing directory and then transfer and then unzip at destination
        print("here1")
        scp(files, TARGETLOCATION, USERNAME, PASSWORD, TARGET_COMPUTER, DATALOCATION, targetSyncCheckFile, syncCheck)

    if os.path.isfile(f"{DATALOCATION}{targetSyncCheckFile}"):
        TargetCheck = subprocess.run(["scp", f"{DATALOCATION}{syncCheck}", f"{USERNAME}@{TARGET_COMPUTER}:{DATALOCATION}{syncCheck}"], stdout=subprocess.PIPE) # this will download the checksum file from the target computer 
        print(TargetCheck.stdout) 




if __name__ == "__main__":
    try:
        if str(os.getcwd) != '/home/robot/Downloads/git/cSync/src':
            print(os.getcwd())
            os.chdir("src")
            print(os.getcwd())
        else:
            pass
    except:
        pass
    if not os.path.exists("data"):
        os.makedirs("data")

    main()


