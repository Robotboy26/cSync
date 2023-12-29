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
import argparse
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
load_dotenv() # load the .env file

tTimeS = time.time()

def calculate_md5(file_path):
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

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

def getChecksumFile(location, syncCheckFile, targetSyncCheckFile, USERNAME, TARGET_COMPUTER):
    checksum = subprocess.run(["scp", f"{USERNAME}@{TARGET_COMPUTER}:{location}/{syncCheckFile}", f"./{targetSyncCheckFile}"], stdout=subprocess.PIPE) # this will download the checksum file from the target computer 
    print(checksum.stdout) 

def scp(files, basePath, targetPath, USERNAME, PASSWORD, TARGET_COMPUTER, removeFiles=None):
    with pysftp.Connection(TARGET_COMPUTER, username=USERNAME, private_key='~/.ssh/id_rsa', private_key_pass=f"{PASSWORD}") as sftp:
        with sftp.cd(targetPath):
            if removeFiles != None:
                for removeF in removeFiles:
                    removeRelitive = stringFromEnd(removeF, basePath)
                    removeRelitive = removeRelitive[1:]
                    print(f"removing: {removeRelitive}")
                    sftp.remove(removeRelitive)

            for send in files:
                end = stringFromEnd(send, basePath)
                end = removeFileFromEnd(end)
                sendWithout = removeFileFromEnd(send)
                sendRelitive = stringFromEnd(sendWithout, basePath)
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
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            results = executor.map(sftp.put, send)
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

def main():
    TARGET_COMPUTER = os.getenv('TARGET_COMPUTER')
    USERNAME = os.getenv('USERNAME')
    PASSWORD = os.getenv('PASSWORD')
    parser = argparse.ArgumentParser(description="Sync files between local and remote directories.")
    parser.add_argument('folderPath', metavar='folderPath', type=str, nargs='?',
                        help='the local directory to be synced')
    parser.add_argument('-d', '--destination', type=str, help='Specify the destination in format <username@ip>')
    args = parser.parse_args()

    if args.destination:
        dest = args.destination
        username, target = dest.split("@")
    else:
        username, target = None, None

    # if args not pass the args from the .env file
    if username == None and target == None:
        username = USERNAME
        target = TARGET_COMPUTER

    if PASSWORD == None:
        password = input(f"type the password for {username} at {target}: ")
    else:
        password = PASSWORD

    syncFile = "data/sync.csync"
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
    genCheckFile(files, md5s, sha256s, syncCheckFile)
    getChecksumFile(f"~/{targetPath}", f"cSync/src/{syncCheckFile}", targetSyncCheckFile, username, target)
    if os.path.isfile(targetSyncCheckFile):
        if quickCompareCheck(syncCheckFile, targetSyncCheckFile):
            os.remove(targetSyncCheckFile) # remove the check file gotten from the target computer once it is does being used
            quit("You are already synced")
        else:
            modifiedFiles, removeFiles = fullCompareCheck(syncCheckFile, targetSyncCheckFile)
            print("here2")
            scp(modifiedFiles, folderPath, targetPath, username, password, target, removeFiles)
            os.remove(targetSyncCheckFile) # remove the check file gotten from the target computer once it is does being used
            print(f"sync took {time.time() - tTimeS}")
            quit("synced all files")
    else:
        # if this is the case that assume that it has never synced before and zip the containing directory and then transfer and then unzip at destination
        print("here1")
        scp(files, folderPath, targetPath, username, password, target)


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
