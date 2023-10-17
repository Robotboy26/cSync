#cSync

#Features
1. sync all file in a directory from one computer to another

#Limitations
1. It only tranfers one way.
2. Is a file is deleted at the target the program does not yet know this and will not resend the file.
3. This project assumes that you have setup ssh key on both computers and they are both finger printed.
4. This project need the target computer on the same network weather this is a vpn or you are just on the local network.
5. Right now this project exspects things to be in the same spot on both of the computers and even the username being incorrect.
6. Right now both computers need to be linux.

#Why
Q: with all of these limitations why should I use this software?
A: you shouldn't. At least in it's current state this software is super hard to use and you might just mess thing up on your computer.

#How To Use
1. open the example.env file in the /src directory
2. run 'cp example.env .env'
3. cd into the /src directory and run 'python3 main.py' this will open a directory selector or if you already know the directory that you want to use do 'python3 main.py <directory>'

#Todo
1. change the file paths in all of the sync files and checksum files to be relitive from the base path so that limitation 5 goes away.
2. change the 2 times that I use the scp command and change it to pysftp to hopfully make it so that you don't need them both to be linux computers and I will need to make the file paths relitive as well if I want to do this(might also need on the fly file decloration conversions not sure).
3. See if I can make this in a way where it will be able to be stoped mid run and restarted later to leave of where it stoped I might need to make a log file type thing so that I can figure out where I left off last time
4. add somthing that will tell the use how many deletions additions and changed in files
5. add zipping so that it can use less network traffic and tranfer small files faster
6. there are many more things that I could do I might add here later or just do them then push
