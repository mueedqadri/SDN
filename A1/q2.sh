#forward path
sh ovs-ofctl add-flow s1 in_port=1,actions=output:3
sh ovs-ofctl add-flow s3 in_port=3,actions=output:2
sh ovs-ofctl add-flow s2 in_port=3,actions=output:1

#return path
sh ovs-ofctl add-flow s2 in_port=1,actions=output:2
sh ovs-ofctl add-flow s1 in_port=2,actions=output:1