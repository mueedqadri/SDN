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
		self.switches = {}

		
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
		priority= 0
		#Process switch connection 
		datapath = ev.msg.datapath
		self.switches[datapath.id] = datapath
		ofproto = datapath.ofproto	
		parser = datapath.ofproto_parser

		#Add default rule
		match = parser.OFPMatch()	
		actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
						  				  ofproto.OFPCML_NO_BUFFER)]
		self.add_flow(datapath, priority, match, actions)


	@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
	def _packet_in_handler(self, ev):
		msg = ev.msg
		datapath = msg.datapath
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		pkt = packet.Packet(msg.data)
		eth = pkt.get_protocol(ethernet.ethernet)

		dpid = datapath.id
		src = eth.src
		dst = eth.dst

		if src not in self.net:
			self.net.add_node(src)
			self.net.add_edge(dpid,src,port=ofproto.OFPXMT_OFB_IN_PHY_PORT)
			self.net.add_edge(src,dpid)

		if dst in self.net:
			src_id = list(self.net[src].keys())[0]
			dst_id = list(self.net[dst].keys())[0]

			# NOTE : As it was mentioned that we do not need to send the packet out
			# therefore when we do the pingall for the first time it sets up all the routes 
			# but the pingall itself (for the first time) does not work. Once all the 
			# routes are setup and we run pingall again, everything works as intented.

			if nx.has_path(self.net, src, dst):
				#-----------------------------------------------------------
				# STEP 1: - compute shortest path between src and dst
				#-----------------------------------------------------------
				path = nx.shortest_path(self.net, src, dst)[1:-1]
				match = parser.OFPMatch(eth_dst=dst, eth_src= src)	

				#------------------------------------------------------------------------
				# STEP 2: - install a routing rule for every switch in the path
				#------------------------------------------------------------------------
			
				for switch_id in path:
					idx =  path.index(switch_id)
					priority= 1
					datapath_curr = self.switches[switch_id]
					if  idx == len(path)-1:
						port = self.net[switch_id][dst]['port']
					else:
						port = self.net[switch_id][path[idx+1]]['port']
					actions = [parser.OFPActionOutput(port)]
					self.add_flow(datapath_curr, priority, match, actions)
			#------------------------------------------------------------------------
			# STEP 3: - install a firewall rule in the ingress switch (i.e., 
			#                first switch in the path), if needed
			#------------------------------------------------------------------------
			if not((src_id%2 and dst_id%2) or not(src_id% 2 or dst_id%2)):
				actions = []
				priority= 2
				match = parser.OFPMatch(eth_dst=dst, eth_src= src)	
				self.add_flow(datapath, priority, match, actions)

	def add_flow(self, datapath, priority, match, actions):
			ofproto = datapath.ofproto
			parser = datapath.ofproto_parser

			inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
								actions)]

			mod = parser.OFPFlowMod(datapath=datapath, priority=priority
						, match=match, 
						instructions=inst)

			datapath.send_msg(mod)



