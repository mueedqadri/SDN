#!/usr/bin/python

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller import ofp_event

from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link

from ryu.lib.packet import packet

#------------------------------------------------------------
# STEP 3: import libraries for parsing L3/L4 headers
#------------------------------------------------------------
from ryu.lib.packet import ethernet, ipv4, tcp

import networkx as nx

class Controller1(app_manager.RyuApp):

	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

	def __init__(self, *args, **kwargs):
		super(Controller1, self).__init__(*args, **kwargs)
		self.topology_api_app = self
		self.net = nx.DiGraph()

		
	@set_ev_cls(event.EventSwitchEnter)
	def get_topology_data(self, ev):
		switch_list = get_switch(self.topology_api_app, None)
		switches = [switch.dp.id for switch in switch_list]
		self.net.add_nodes_from(switches)

		link_list = get_link(self.topology_api_app, None)

		for link in link_list:
			self.net.add_edge(link.src.dpid, link.dst.dpid, port=link.src.port_no)
			self.net.add_edge(link.dst.dpid, link.src.dpid, port=link.dst.port_no)


	@set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
	def switch_features_handler(self, ev):
		#Process switch connection 
		datapath = ev.msg.datapath
		ofproto = datapath.ofproto	
		parser = datapath.ofproto_parser

		#------------------------------------------------------------
		# STEP 1: TODO - add different default rules for odd and even nodes
		#------------------------------------------------------------
		match = parser.OFPMatch()	

		actions = [parser.OFPInstructionGotoTable(0)]
		self.add_flow(datapath, 0, 0, match, actions)

		actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
						  ofproto.OFPCML_NO_BUFFER)]
		self.add_flow(datapath, 0, 1, match, actions)



	@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
	def _packet_in_handler(self, ev):
		msg = ev.msg
		datapath = msg.datapath
		ofproto = datapath.ofproto

		pkt = packet.Packet(msg.data)
		eth = pkt.get_protocol(ethernet.ethernet)

		#--------------------------------------------------
		# STEP 4: TODO - parse upper layer info
		#--------------------------------------------------

		dpid = datapath.id
		src = eth.src
		dst = eth.dst

		#Add end hosts to discovered topo
		if src not in self.net:
			self.net.add_node(src)
			self.net.add_edge(dpid,src,port=msg.match['in_port'])
			self.net.add_edge(src,dpid)

			print(">>>> Nodes <<<<")
			print(self.net.nodes())
			print(">>>> Edges <<<<")
			print(self.net.edges())
		
		#--------------------------------------------------
		# STEP 5a: check whether tcp packet
		#--------------------------------------------------		
		elif src in self.net and dst in self.net and tcp_info != None:
			print(">>>> Add your logic here <<<<")

			#--------------------------------------------------
			# STEP 5b: TODO - implement routing logic
			#--------------------------------------------------


			#Forward original packet
			parser = datapath.ofproto_parser

			out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=msg.match['in_port'], actions=actions)
			datapath.send_msg(out)


	#----------------------------------------------------------
	# STEP 6: add helper function to check whether odd or even
	#----------------------------------------------------------
	def isEven(self, portNumber):
		if portNumber % 2 == 0:
			return True
		else:
			return False

	#--------------------------------------------------
	# STEP 2: TODO - add helper function for goto instruction
	#--------------------------------------------------
	def add_flow_goto(self, datapath, priority, tableID, match, dstTable):


	#--------------------------------------------------
	# STEP 7: TODO - add table ID info to new rules
	#--------------------------------------------------
	def add_flow(self, datapath, priority, tableID, match, actions):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		#Construct flow_mod message and send it
		inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
						     actions)]

		mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
					match=match, 
					instructions=inst)

		datapath.send_msg(mod)










