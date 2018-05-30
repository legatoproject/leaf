How to add an external command to leaf
- Add an executable into 'extensions/' folder
- The executable file name must start with 'leaf-'
  the executable can have any extension '.sh', '.bin' ... it will be stripped by leaf
  for example 'leaf-mycommand.sh', 'mycommand' being the command name, runnable with 'leaf mycommand'
- The executable must handle '--help' argument to display some documentation 
  only the first line will be displayed in 'leaf --help'
  full documentation will be displayed with 'leaf mycommand --help'
- Add the command name to 'src/leaf/cli.py' enabled command array (see comment in main function to append 'mycommand')
- Add a line 'leaf-mycommand.sh  usr/local/bin/' in the debian package install file 'packaging/extrafiles/debian/install'
