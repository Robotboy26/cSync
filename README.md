#cSync

#Features
1. sync all file in a directory from one computer to another

#Limitations
1. It is only one way
2. Is a file is deleted at the target the program does not yet know this and will not resend the file
3. This project assumes that you have setup ssh key on both computers and they are both finger printed
4. This project need the target computer on the same network weather this is a vpn or you are just on the local network
5. This project needs things to be in the same spot on both computers if you want updateCheck.py to work

#Why
Q: with all of these limitations why should I use this software?
A: you shouldn't. At least in it's current state this software is super hard to use and you might just mess thing up on your computer.

#How To Use
1. open the example.env file in the /src directory
2. run 'cp example.env .env'
3. cd into the /src directory and run 'python3 main.py' this will open a directory selector or if you already know the directory that you want to use do 'python3 main.py <directory>'
