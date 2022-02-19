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
from ryu.lib import hub

import networkx as nx

class Controller1(app_manager.RyuApp):

	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

	def __init__(self, *args, **kwargs):
		super(Controller1, self).__init__(*args, **kwargs)
		self.topology_api_app = self
		self.net = nx.DiGraph()
		self.switches = {}
		self.datapaths = {}

		## Monitor threads
		self.monitor_thread = hub.spawn(self._monitor)

	#--------------------------------------
	# STEP 2b: store switch datapaths
	#--------------------------------------
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

		#Add default rule for table 0
		match = parser.OFPMatch()	
		tableID = 0
		self.add_flow_goto(datapath, 0, tableID, match, 1)

		#Add default rule for table 1
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
			print(">> Nodes <<")
			print(self.net.nodes())
			print(">> Edges <<")
			print(self.net.edges())
			#print(type(self.net.edges()))


		if dst in self.net:

			
			#-----------------------------------------------------------
			# STEP 1: TODO - compute shortest path between src
			#-----------------------------------------------------------
			shortestPath2 = nx.shortest_path(self.net,src,dst)
			print("Shortest Path between SRC and DST : \t",shortestPath2)

			shortestPath = shortestPath2[1:-1]
			parser = datapath.ofproto_parser

			#------------------------------------------------------------------------
			# STEP 2 & 3: TODO - install a routing rule for every switch in the path & 
			#					install a firewall rule in the ingress switch (i.e., 
			#                	first switch in the path), if needed
			#------------------------------------------------------------------------
			index=0;
			if((shortestPath[0] + shortestPath[len(shortestPath)-1]) % 2 == 0):
				tableID=1;
				for i in shortestPath:
					datapath2 = self.switches[i];
					rulePrinter = "";

					if index != len(shortestPath)-1:
						out_port=self.net[i][shortestPath[index+1]]['port']
						match = parser.OFPMatch(eth_src=src, eth_dst=dst)
						actions = [parser.OFPActionOutput(out_port)]
						rulePrinter = rulePrinter + "Added rule: \n switch:"+str(i)+" output port:"+str(out_port)

					if(index == len(shortestPath)-1):
						actions.append(parser.OFPActionOutput(1))
						rulePrinter = rulePrinter +", output port:"+str(1)
						
					self.add_flow(datapath2, 1, tableID, match, actions)
					print(rulePrinter)
					index=index+1;
					out = parser.OFPPacketOut(datapath=datapath2, buffer_id=msg.buffer_id, in_port=msg.match['in_port'], actions=actions)
					datapath2.send_msg(out)
						
			else:
				tableID = 0;
				actions = []
				match = parser.OFPMatch(eth_src=src, eth_dst=dst)
				self.add_flow(datapath, 2, tableID, match, actions)
				rulePrinter = "Drop Rule for : ";
				rulePrinter = rulePrinter , "switch:",str(shortestPath[0])," SRC: ",str(src)," DST: ",str(dst)
				print(rulePrinter)
			
			

				
	def isEven(self, nodeId):
		if nodeId % 2 == 0:
			return True
		else:
			return False

	#--------------------------------------------------
	# STEP 2: add helper function for goto instruction
	#--------------------------------------------------
	def add_flow_goto(self, datapath, priority, tableID, match, dstTable):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		#Complete here
		inst = [parser.OFPInstructionGotoTable(dstTable)]

		mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
					table_id=tableID, match=match, 
					instructions=inst)

		datapath.send_msg(mod)


	#--------------------------------------------------
	# STEP 7: add table ID info to new rules
	#--------------------------------------------------
	def add_flow(self, datapath, priority, tableID, match, actions):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		#Construct flow_mod message and send it
		inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
						     actions)]

		mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
					table_id=tableID, match=match, 
					instructions=inst)

		datapath.send_msg(mod)
	#--------------------------------------
	# STEP 4: define monitoring function
	#--------------------------------------
	def _monitor(self):
		while True:
			for dp in self.switches.values():
				self._request_stats(dp)
			hub.sleep(5)


	#--------------------------------------
	# STEP 5: send stats request
	#--------------------------------------
	def _request_stats(self, datapath):
		self.logger.debug('send stats request: %016x', datapath.id)
		if(datapath.id==5):
			print('send stats request: %016x', datapath.id)
			ofproto = datapath.ofproto
			parser = datapath.ofproto_parser
			req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
			datapath.send_msg(req)


	#--------------------------------------
	# STEP 6: process stats reply
	#--------------------------------------
	@set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
	def port_stats_reply_handler(self, ev):

		print('--------------------------'
			  '--------------------------'
			  '---------')
		print('\t\t >>>>> PORT STATS - S%d <<<<<' %ev.msg.datapath.id)
		print('--------------------------'
			  '--------------------------'
			  '---------')

		ports = []
		for stat in ev.msg.body:
			ports.append('port_no=%d '
						 'rx_packets=%d '%
						 (stat.port_no,
                      	  stat.rx_packets))
			self.logger.debug('PortStats: %s', ports)
		print('PortStats: %s',ports)
	#	self.logger.info('datapath         '
	#					'eth-dst           '
	#					'out-port packets  bytes')
	#	self.logger.info('---------------- '
			#			'----------------- '
			#			'-------- -------- --------')

	#	body = ev.msg.body

	#	for flow in body:
	#		if flow.priority == 1:
	#			self.logger.info('%016X %17s %8x %8d %8d',
 	#						ev.msg.datapath.id,
	#						flow.match['eth_dst'],
	#						flow.instructions[0].actions[0].port,
	#						flow.packet_count, flow.byte_count)
		
	#	print('\n')		