#!/usr/bin/python

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller import ofp_event

from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link

from ryu.lib.packet import packet
from ryu.lib.packet import ethernet

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

		#Add default rule
		match = parser.OFPMatch()	
		actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
						  ofproto.OFPCML_NO_BUFFER)]
			
		self.add_flow(datapath, 0, match, actions)


	@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
	def _packet_in_handler(self, ev):
		msg = ev.msg
		datapath = msg.datapath
		ofproto = datapath.ofproto

		pkt = packet.Packet(msg.data)
		eth = pkt.get_protocol(ethernet.ethernet)

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
		
		elif src in self.net and dst in self.net:
			print(">>>> Add your logic here <<<<")

			#------------------------------------------------
			# STEP 1: send packets to group table (group 1)
			#------------------------------------------------
			parser = datapath.ofproto_parser
			match = parser.OFPMatch(eth_dst=dst)	
			actions = [parser.OFPActionGroup(1)]
			self.add_flow(datapath, 1, match, actions)

			#---------------------------------------------------------
			# STEP 2: configure group entry (i.e., install FFG rule)
			#---------------------------------------------------------
			parser = datapath.ofproto_parser			
			actions1 = [parser.OFPActionSetField(eth_dst='00:00:00:00:00:02'), 
				    parser.OFPActionSetField(ipv4_dst="10.0.0.2"),
				    parser.OFPActionOutput(2)]
			actions2 = [parser.OFPActionSetField(eth_dst='00:00:00:00:00:03'),
				    parser.OFPActionSetField(ipv4_dst="10.0.0.3"),
				    parser.OFPActionOutput(3)]
			buckets = [parser.OFPBucket(0, 2, 0, actions1),
				   parser.OFPBucket(0, 3, 0, actions2)]
			self.add_group(datapath, 1, buckets)


	#---------------------------------------------------------
	# STEP 3: install group rule
	#---------------------------------------------------------			
	def add_group(self, datapath, group_id, buckets):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		req = parser.OFPGroupMod(datapath, ofproto.OFPGC_ADD,
                                 ofproto.OFPGT_FF, group_id, buckets)
		out = datapath.send_msg(req)


	def add_flow(self, datapath, priority, match, actions):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		#Construct flow_mod message and send it
		inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
						     actions)]

		mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
					match=match, instructions=inst)

		datapath.send_msg(mod)











