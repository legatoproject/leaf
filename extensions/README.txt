How to add an external command to leaf
- Add an executable into 'extensions/' folder
- The executable file name must start with 'leaf-'
  for example 'leaf-mycommand', 'mycommand' being the command name, runnable with 'leaf mycommand'
- The executable must handle '--description' argument to display some documentation 
  only the first line will be displayed in 'leaf --help'
  full documentation will be displayed with 'leaf mycommand --help' if implemented in your script
- Add a line 'leaf-mycommand  usr/local/bin/' in the debian package install file 'packaging/extrafiles/debian/install'
