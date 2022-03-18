To run either of the solution we need to initialize
the virtual interfaces using the command below:

    sudo ./veth_setup.sh


*********************Q1*************************** 
Step 1 Compile: 

    p4c --target bmv2 --arch v1model q1.p4


Step 2 Run: 

    sudo simple_switch -i 1@veth0 -i 2@veth2 -i 3@veth4 -i 4@veth6 --log-console --thrift-port 9090 q1.json


Step 3 Run: 

    sudo simple_switch_CLI --thrift-port 9090 < commands.txt

Step 4 Send Packets:

    sudo ./send.py



**********************Q2*****************************

Step 1 Compile: 

    p4c --target bmv2 --arch v1model q1.p4


Step 2 Run: 

    sudo simple_switch -i 1@veth0 -i 2@veth2 --log-console --thrift-port 9090 q2.json


Step 3 Run: 

    sudo simple_switch_CLI --thrift-port 9090 < commands.txt

Step 4 Send Packets:

    sudo ./send.py 10.0.0.2 "Test packet"