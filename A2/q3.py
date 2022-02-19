#!/usr/bin/python

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER
from ryu.controller import ofp_event

from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link

from ryu.lib.packet import packet
from ryu.lib.packet import ethernet

import networkx as nx
from ryu.lib import hub

class Controller1(app_manager.RyuApp):

	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

	def __init__(self, *args, **kwargs):
		super(Controller1, self).__init__(*args, **kwargs)
		self.topology_api_app = self
		self.net = nx.DiGraph()
		self.switches = {}
		self.datapaths = {}
		self.monitor_thread = hub.spawn(self._monitor)

	@set_ev_cls(ofp_event.EventOFPStateChange,
				[MAIN_DISPATCHER, DEAD_DISPATCHER])
	def _state_change_handler(self, ev):
		datapath = ev.datapath
		if ev.state == MAIN_DISPATCHER:
			if datapath.id not in self.datapaths:
				self.logger.debug('register datapath: %016x', datapath.id)
				self.datapaths[datapath.id] = datapath
		elif ev.state == DEAD_DISPATCHER:
			if datapath.id in self.datapaths:
				self.logger.debug('unregister datapath: %016x', datapath.id)
				del self.datapaths[datapath.id]

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

		tableID = 0
		self.add_flow_goto(datapath, 0, tableID, match, 1)

		match = parser.OFPMatch()	
		actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
  				  ofproto.OFPCML_NO_BUFFER)]
			
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
			if nx.has_path(self.net, src, dst):
				path = nx.shortest_path(self.net, src, dst)[1:-1]
				match = parser.OFPMatch(eth_dst=dst, eth_src= src)	

				for switch_id in path:
					idx =  path.index(switch_id)
					priority= 1
					table_id = 1
					datapath_curr = self.switches[switch_id]
					if  idx == len(path)-1:
						port = self.net[switch_id][dst]['port']
					else:
						port = self.net[switch_id][path[idx+1]]['port']
					actions = [parser.OFPActionOutput(port)]
					self.add_flow(datapath_curr, priority, table_id, match, actions)
					
			if not((src_id%2 and dst_id%2) or not(src_id% 2 or dst_id%2)):
				actions = []
				priority= 1
				table_id = 0
				match = parser.OFPMatch(eth_dst=dst, eth_src= src)	
				self.add_flow(datapath, priority, table_id, match, actions)

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


	def _monitor(self):
			while True:	
				if self.switches:
					self._request_stats(self.switches[5])
				hub.sleep(5)

	def _request_stats(self, datapath):
		self.logger.debug('send stats request: %016x', datapath.id)
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		req = parser.OFPPortStatsRequest(datapath)
		datapath.send_msg(req)

	@set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
	def _flow_stats_reply_handler(self, ev):

		print('------------------'
			  '------------------'
			  '---------')
		print('\t >>>>> PORT STATS - S%d <<<<<' %ev.msg.datapath.id)
		print('--------------------------'
			  '--------------------------')
		self.logger.info('datapath         '
						'port_no           '
						'rx_packets')
		self.logger.info('---------------- '
						'----------------- '
						'-------- ')
		body = ev.msg.body
		for port in body:
			self.logger.info('%016X %17s %8x ',
					ev.msg.datapath.id,
					port.port_no,
					port.rx_packets,)
		
		print('\n')
