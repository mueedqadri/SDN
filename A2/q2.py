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
		#Process switch connection 
		datapath = ev.msg.datapath
		self.switches[datapath.id] = datapath
		ofproto = datapath.ofproto	
		parser = datapath.ofproto_parser

		match = parser.OFPMatch()	

		#Default rule in table 0 to send packets to table 1
		tableID = 0
		self.add_flow_goto(datapath, 0, tableID, match, 1)

		match = parser.OFPMatch()	
		actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
  				  ofproto.OFPCML_NO_BUFFER)]
			
		#Default rule in table 1 to send packets to the controller
		tableID = 1
		self.add_flow(datapath, 0, tableID, match, actions)


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
			if not((src_id%2 and dst_id%2) or not(src_id% 2 or dst_id%2)):
				# firewall rule in table 0 to drop the packets
				print('block')
				tableID = 0
				actions = []
				match = parser.OFPMatch(eth_dst=dst, eth_src= src)	
				self.add_flow(datapath, 1, tableID, match, actions)

			elif nx.has_path(self.net, src, dst):
				# shortest path computation
				path = nx.shortest_path(self.net, src, dst)
				for idx, switch in enumerate(path):
					if(switch == dpid):
						# routing rule for table 1 to forward the packets
						print('Switch: ', self.net[switch])
						port = self.net[switch][path[idx+1]]['port']
						if idx == 1 or idx == len(path)-2:
							actions = [parser.OFPActionOutput(port), parser.OFPActionOutput(1)]
						else:
							actions = [parser.OFPActionOutput(port)]
						match = parser.OFPMatch(eth_dst=dst)	
						tableID = 1
						self.add_flow(datapath, 1, tableID, match, actions)

	def add_flow(self, datapath, priority, tableID, match, actions):
			ofproto = datapath.ofproto
			parser = datapath.ofproto_parser

			inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
								actions)]

			mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
						table_id=tableID, match=match, 
						instructions=inst)

			datapath.send_msg(mod)

	def add_flow_goto(self, datapath, priority, tableID, match, dstTable):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		#Complete here
		inst = [parser.OFPInstructionGotoTable(dstTable)]

		mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
					table_id=tableID, match=match, 
					instructions=inst)

		datapath.send_msg(mod)








