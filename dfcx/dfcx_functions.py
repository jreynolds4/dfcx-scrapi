#!/usr/bin/env python
# coding: utf-8

import copy
import json
import logging
import os
import sys
import pandas as pd
import pathlib
import requests
import subprocess
import time
from collections import defaultdict
from typing import Dict, List
from .dfcx import DialogflowCX

import google.cloud.dialogflowcx_v3beta1.types as types

# logging config
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

class DialogflowFunctions:
    def __init__(self, creds, agent_id=None):
            
        with open(creds) as json_file:
            data = json.load(json_file)
        project_id = data['project_id']
        
        self.project_id = 'projects/{}/locations/global'.format(project_id)

        if agent_id:
            self.dfcx = DialogflowCX(creds, agent_id)
            self.agent_id = self.project_id + agent_id

        else:
            self.dfcx = DialogflowCX(creds)
    

### TODO: (pmarlow@) move this to @staticmethod outside of main function.
### perhaps move to the main dfcx.py file as a @staticmethod ?

    def get_flows_map(self, agent_id, reverse=False):
        """ Exports Agent Flow Names and UUIDs into a user friendly dict.
        
        Args:
          - agent_id, the formatted CX Agent ID to use
          - reverse, (Optional) Boolean flag to swap key:value -> value:key
          
        Returns:
          - flows_map, Dictionary containing flow UUIDs as keys and 
              flow.display_name as values
          """
        
        if reverse:
            flows_dict = {flow.display_name:flow.name
                          for flow in self.dfcx.list_flows(agent_id)}
            
        else:
            flows_dict = {flow.name:flow.display_name
                         for flow in self.dfcx.list_flows(agent_id)}
        
        return flows_dict
    
    
    def get_intents_map(self, agent_id, reverse=False):
        """ Exports Agent Intent Names and UUIDs into a user friendly dict.
        
        Args:
          - agent_id, the formatted CX Agent ID to use
          - reverse, (Optional) Boolean flag to swap key:value -> value:key
          
        Returns:
          - intents_map, Dictionary containing Intent UUIDs as keys and 
              intent.display_name as values
          """
        
        if reverse:
            intents_dict = {intent.display_name:intent.name
                            for intent in self.dfcx.list_intents(agent_id)}
        
        else:
            intents_dict = {intent.name:intent.display_name
                       for intent in self.dfcx.list_intents(agent_id)}
        
        return intents_dict
    

    def get_entities_map(self, agent_id, reverse=False):
        """ Exports Agent Entityt Names and UUIDs into a user friendly dict.
        
        Args:
          - agent_id, the formatted CX Agent ID to use
          - reverse, (Optional) Boolean flag to swap key:value -> value:key
          
        Returns:
          - intents_map, Dictionary containing Entity UUIDs as keys and 
              intent.display_name as values
          """
        
        if reverse:
            entities_dict = {entity.display_name:entity.name
                            for entity in self.dfcx.list_entity_types(agent_id)}
        
        else:
            entities_dict = {entity.name:entity.display_name
                       for entity in self.dfcx.list_entity_types(agent_id)}
        
        return entities_dict
    

    def get_webhooks_map(self, agent_id, reverse=False):
        """ Exports Agent Webhook Names and UUIDs into a user friendly dict.
        
        Args:
          - agent_id, the formatted CX Agent ID to use
          - reverse, (Optional) Boolean flag to swap key:value -> value:key
          
        Returns:
          - webhooks_map, Dictionary containing Webhook UUIDs as keys and
              webhook.display_name as values
          """
        
        if reverse:
            webhooks_dict = {webhook.display_name:webhook.name
                             for webhook in self.dfcx.list_webhooks(agent_id)}
            
        else:
            webhooks_dict = {webhook.name:webhook.display_name
                             for webhook in self.dfcx.list_webhooks(agent_id)}
        
        return webhooks_dict
    

    def get_pages_map(self, flow_id, reverse=False):
        """ Exports Agent Page UUIDs and Names into a user friendly dict.
        
        Args:
          - flow_id, the formatted CX Agent Flow ID to use
          - reverse, (Optional) Boolean flag to swap key:value -> value:key
          
        Returns:
          - webhooks_map, Dictionary containing Webhook UUIDs as keys and
              webhook.display_name as values. If Optional reverse=True, the 
              output will return page_name:ID mapping instead of ID:page_name
          """
        
        if reverse:
            pages_dict = {page.display_name:page.name
                          for page in self.dfcx.list_pages(flow_id)}
            
        else:
            pages_dict = {page.name:page.display_name
                          for page in self.dfcx.list_pages(flow_id)}
            
        return pages_dict
    

    def get_route_groups_map(self, flow_id, reverse=False):
        """ Exports Agent Route Group UUIDs and Names into a user friendly dict.
        
        Args:
          - flow_id, the formatted CX Agent Flow ID to use
          - reverse, (Optional) Boolean flag to swap key:value -> value:key
          
        Returns:
          - webhooks_map, Dictionary containing Webhook UUIDs as keys and
              webhook.display_name as values. If Optional reverse=True, the 
              output will return page_name:ID mapping instead of ID:page_name
          """
        
        if reverse:
            pages_dict = {page.display_name:page.name
                          for page in self.dfcx.list_transition_route_groups(flow_id)}
            
        else:
            pages_dict = {page.name:page.display_name
                          for page in self.dfcx.list_transition_route_groups(flow_id)}
            
        return pages_dict
    
# COPY FUNCTIONS

    def copy_intent_to_agent(self, intent_display_name, source_agent, destination_agent):
        # retrieve from source agent
        intents_map = self.get_intents_map(source_agent, reverse=True)
        intent_id = intents_map[intent_display_name]
        intent_object = self.dfcx.get_intent(intent_id)
        
        if 'parameters' in intent_object:
            source_entities_map = self.get_entities_map(source_agent)
            destination_entities_map = self.get_entities_map(destination_agent, reverse=True)
            
            for param in intent_object.parameters:
                if 'sys.' in param.entity_type:
                    pass
                else:
                    source_name = source_entities_map[param.entity_type]
                    destination_name = destination_entities_map[source_name]
                    param.entity_type = destination_name

        # push to destination agent
        try:
            self.dfcx.create_intent(destination_agent, intent_object)
            logging.info('Intent \'{}\' created successfully'.format(intent_object.display_name))
        except Exception as e:
            print(e)
            print('If you are trying to update an existing Intent, see method dfcx.update_intent()')
            
            
    def copy_entity_type_to_agent(self, entity_type_display_name, source_agent, destination_agent):
        # retrieve from source agent
        entity_map = self.get_entities_map(source_agent, reverse=True)
        entity_id = entity_map[entity_type_display_name]
        entity_object = self.dfcx.get_entity_type(entity_id)
        

        # push to destination agent
        try:
            self.dfcx.create_entity_type(destination_agent, entity_object)
            logging.info('Entity Type \'{}\' created successfully'.format(entity_object.display_name))
        except:
            logging.info('Entity Type \'{}\' already exists in agent'.format(entity_object.display_name))
            logging.info('If you are trying to update an existing Entity, see method dfcx.update_entity_type()')
            
            
    def create_page_shells(self, pages_list: List[types.Page], destination_agent: str, destination_flow: str ='Default Start Flow'):
        """ Create blank DFCX Page object(s) with given Display Name.

        This function aids in the copy/pasting of pages from one DFCX agent to
        another by first creating blank Page "shells" in the destination agent
        using the human-readable display names. These Pages will then be retrieved
        by Page ID to use in the final copy/paste of the Page object from source to
        destination.

        Args:
          pages_list, List of Page(s) object to extract page names from
          destination_agent, DFCX Agent ID of the Destination Agent
          destination_flow, DFCX Flow ID of the Destination Flow. If no Flow ID is
            provided, Default Start Flow will be used.

        Returns:
          Success!
        """
        
        destination_flows = self.get_flows_map(destination_agent, reverse=True)
        
        for page in pages_list:
            try:
                self.dfcx.create_page(destination_flows[destination_flow], display_name=page.display_name)
                logging.info('Page \'{}\' created successfully'.format(page.display_name))
            except Exception as e:
                logging.info(e)
                logging.info('Page \'{}\' already exists in agent'.format(page.display_name))
                continue
                
                
    def copy_paste_agent_resources(self, resource_dict: Dict[str,str],
                                   source_agent: str, destination_agent: str,
                                   destination_flow: str='Default Start Flow',
                                   skip_list: List[str]=[]):
        """ Copy/Paste Agent level resources from one DFCX agent to another.
        
        Agent level resources in DFCX are resources like Entities, Intents, and
        Webhooks which are not Flow dependent. This method allows the user to 
        provide a dictionary of Agent Resources and Resources IDs to be copied
        from a Source agent to a Destination agent. *NOTE* That this method
        will also copy all Route Groups from Default Start Flow only.
        
        To obtain the resource_dict in the proper format, you can use the
        get_page_dependencies() method included in the DFFX library.
        
        Args:
          resource_dict: Dictionary of Lists of DFCX Resource IDs with keys
            corresponding to the Resource type (i.e. intents, entities, etc.)
            and values corresponding to the Resource ID itself.
          source_agent: DFCX Source Agent ID (Name)
          destination_agent: DFCX Destination Agent ID (Name)
          destination_flow: (Optional) Defaults to 'Default Start Flow'
          skip_list: (Optional) List of resources to exclude. Use the following
              strings: 'intents', 'entities', 'webhooks', 'route_groups'
          
        Returns:
          Success!
        """
        resource_obj_dict = defaultdict(list)

        # COPY
        if 'entities' not in skip_list:
            source_entities = self.dfcx.list_entity_types(source_agent)
            for entity in source_entities:
                if entity.name in resource_dict['entities']:
                    resource_obj_dict['entities'].append(entity)
            
        if 'intents' not in skip_list:
            source_intents = self.dfcx.list_intents(source_agent)
            for intent in source_intents:
                if intent.name in resource_dict['intents']:
                    resource_obj_dict['intents'].append(intent)
            
        if 'webhooks' not in skip_list:
            source_webhooks = self.dfcx.list_webhooks(source_agent)
            for webhook in source_webhooks:
                if webhook.name in resource_dict['webhooks']:
                    resource_obj_dict['webhooks'].append(webhook)
        
        if 'route_groups' not in skip_list:
            source_flows_map = self.get_flows_map(source_agent, reverse=True)
            source_route_groups = self.dfcx.list_transition_route_groups(source_flows_map['Default Start Flow'])
            for rg in source_route_groups:
                if rg.name in resource_dict['route_groups']:
                    resource_obj_dict['route_groups'].append(rg)

        ### TODO (pmarlow@): Add more descriptive Error Handling messages
        ### TODO (pmarlow@): Need to identify strategy for dedupe logic / Design Doc
        """ Notes
            - We don't have timestamp to determine when a resource was created so we can't use 'latest'
            - Need to allow user to determine merge strategy depending on type of resource
        """
        # PASTE
        if 'webhooks' in resource_obj_dict and 'webhooks' not in skip_list:
            # Attempt to Create the new Webhook Resource. If the Resource is
            # a duplicate, then we will skip it. Duplicate is determined by
            # display_name only at this time.
            for webhook in resource_obj_dict['webhooks']:
                try:
                    self.dfcx.create_webhook(destination_agent, webhook)
                    logging.info('Webhook \'{}\' created successfully.'.format(webhook.display_name))
                except Exception as e:
                    logging.info(e)
                    logging.info('Webhook \'{}\' already exists in agent'.format(webhook.display_name))
                    pass

        if 'entities' in resource_obj_dict and 'entities' not in skip_list:
            for entity in resource_obj_dict['entities']:
                # Attempt to Create the new Entity Resource. If the Resource is
                # a duplicate, then we will skip it. Duplicate is determined by
                # display_name only at this time.
                try:
                    self.dfcx.create_entity_type(destination_agent, entity)
                    logging.info('Entity \'{}\' created successfully.'.format(entity.display_name))
                except Exception as e:
                    print(e)
                    logging.info('Entity \'{}\' already exists in agent'.format(entity.display_name))
                    pass
                
        if 'intents' in resource_obj_dict and 'intents' not in skip_list:
            source_entities_map = self.get_entities_map(source_agent)
            destination_entities_map = self.get_entities_map(destination_agent, reverse=True)
            for intent in resource_obj_dict['intents']:
                time.sleep(1)
                # If Intents contain Entity tags, we need to convert those to the new Agent ID string
                # Check to see if any Intents need Entity conversion before creating
                if 'parameters' in intent:
                    for param in intent.parameters:
                        if 'sys.' in param.entity_type:
                            pass
                        else:
                            source_name = source_entities_map[param.entity_type]
                            destination_name = destination_entities_map[source_name]
                            param.entity_type = destination_name
                
                # Attempt to Create the new Intent Resource. If the Resource is
                # a duplicate, then we will skip it. Duplicate is determined by
                # display_name only at this time.
                try:
                    self.dfcx.create_intent(destination_agent, intent)
                    logging.info('Intent \'{}\' created successfully'.format(intent.display_name))
                except Exception as e:
                    print(e)
                    logging.info('Intent \'{}\' already exists in agent'.format(intent.display_name))
                    pass
        
        if 'route_groups' in resource_obj_dict and 'route_groups' not in skip_list:
            source_intents_map = self.get_intents_map(source_agent)
            source_webhooks_map = self.get_webhooks_map(source_agent)
            source_pages_map = self.get_pages_map(source_flows_map['Default Start Flow'])

            destination_flows = self.get_flows_map(destination_agent, reverse=True)
            destination_intents_map = self.get_intents_map(destination_agent, reverse=True)
            destination_webhooks_map = self.get_webhooks_map(destination_agent, reverse=True)
            
            destination_pages_map = self.get_pages_map(destination_flows[destination_flow], reverse=True)
            
            for rg in resource_obj_dict['route_groups']:
                for tr in rg.transition_routes:
                    source_name = source_intents_map[tr.intent]
                    destination_name = destination_intents_map[source_name]
                    tr.intent = destination_name
                    
                    if 'trigger_fulfillment' in tr:
                        if 'webhook' in tr.trigger_fulfillment:
                            source_webhook = source_webhooks_map[tr.trigger_fulfillment.webhook]
                            destination_webhook = destination_webhooks_map[source_webhook]
                            tr.trigger_fulfillment.webhook = destination_webhook

                    if 'target_page' in tr:
                        if tr.target_page.split('/')[-1] == 'END_FLOW':
                            tr.target_page = destination_flows[destination_flow] + '/pages/END_FLOW'
                        else:
                            source_page = source_pages_map[tr.target_page]
                            destination_page = destination_pages_map[source_page]
                            tr.target_page = destination_page
                    
                try:
                    self.dfcx.create_transition_route_group(destination_flows[destination_flow], rg)
                    logging.info('Route Group \'{}\' created successfully'.format(rg.display_name))
                except Exception as e:
                    print(e)
                    logging.info('Route Group \'{}\' already exists in agent'.format(rg.display_name))
                    pass
    
    
    def convert_page_dependencies(self, agent_id: str, pages: List[types.Page], agent_type: str='source', flow: str='Default Start Flow') -> List[types.Page]:
        
        pages_mod = copy.deepcopy(pages)

        if agent_type == 'source':
            intents_map = self.get_intents_map(agent_id)
            entities_map = self.get_entities_map(agent_id)
            webhooks_map = self.get_webhooks_map(agent_id)
            flows_map = self.get_flows_map(agent_id, reverse=True)
            pages_map = self.get_pages_map(flows_map[flow])
            rgs_map = self.get_route_groups_map(flows_map[flow])

            # For each page, recurse through the resources and look for
            # specific resource types that will have local agent
            # dependencies, then replace that UUID with a literal
            # str display_name. We will use this display_name to map back
            # to the appropriate destination UUID later.
            for page in pages_mod:
                if 'entry_fulfillment' in page:
                    if 'webhook' in page.entry_fulfillment:
                        page.entry_fulfillment.webhook = webhooks_map[page.entry_fulfillment.webhook]
                
                if 'transition_routes' in page:
                    for tr in page.transition_routes:
                        if 'target_page' in tr:
                            if tr.target_page.split('/')[-1] == 'END_FLOW':
                                tr.target_page = 'END_FLOW'
                                
                            elif tr.target_page.split('/')[-1] == 'END_SESSION':
                                tr.target_page = 'END_SESSION'
                                
                            elif tr.target_page.split('/')[-1] == 'CURRENT_PAGE':
                                tr.target_page = 'CURRENT_PAGE'
                                
                            else:
                                tr.target_page = pages_map[tr.target_page]

                        if 'intent' in tr:
                            tr.intent = intents_map[tr.intent]
                            if 'webhook' in tr.trigger_fulfillment:
                                tr.trigger_fulfillment.webhook = webhooks_map[tr.trigger_fulfillment.webhook]
                        elif 'condition' in tr and 'webhook' in tr.trigger_fulfillment:
                            tr.trigger_fulfillment.webhook = webhooks_map[tr.trigger_fulfillment.webhook]
                            
                if 'event_handlers' in page:
                    for handler in page.event_handlers:
                        if 'target_page' in handler:
                            if handler.target_page.split('/')[-1] == 'END_FLOW':
                                handler.target_page = 'END_FLOW'
                                
                            elif handler.target_page.split('/')[-1] == 'END_SESSION':
                                handler.target_page = 'END_SESSION'
                                
                            elif handler.target_page.split('/')[-1] == 'CURRENT_PAGE':
                                handler.target_page = 'CURRENT_PAGE'
                                
                            else:
                                handler.target_page = pages_map[handler.target_page]
                                
                        if 'trigger_fulfillment' in handler:
                            if 'webhook' in handler.trigger_fulfillment:
                                handler.trigger_fulfillment.webhook = webhooks_map[handler.trigger_fulfillment.webhook]
                                
                if 'form' in page:
                    if 'parameters' in page.form:
                        for param in page.form.parameters:
                            if 'fill_behavior' in param:
                                if 'initial_prompt_fulfillment' in param.fill_behavior:
                                    if 'webhook' in param.fill_behavior.initial_prompt_fulfillment:
                                        param.fill_behavior.initial_prompt_fulfillment.webhook = webhooks_map[param.fill_behavior.initial_prompt_fulfillment.webhook]
                                
                                if 'reprompt_event_handlers' in param.fill_behavior:
                                    for handler in param.fill_behavior.reprompt_event_handlers:
                                        if 'trigger_fulfillment' in handler:
                                            if 'webhook' in handler.trigger_fulfillment:
                                                handler.trigger_fulfillment.webhook = webhooks_map[handler.trigger_fulfillment.webhook]
                                                
                                        if 'target_page' in handler:
                                            print(handler.target_page)
                                            if handler.target_page.split('/')[-1] == 'END_FLOW':
                                                handler.target_page = 'END_FLOW'
                                                
                                            elif handler.target_page.split('/')[-1] == 'END_SESSION':
                                                handler.target_page = 'END_SESSION'
                                                
                                            elif handler.target_page.split('/')[-1] == 'CURRENT_PAGE':
                                                handler.target_page = 'CURRENT_PAGE'
                                                
                                            else:
                                                handler.target_page = pages_map[handler.target_page]
                                            

                            if 'sys.' in param.entity_type:
                                pass
                            else:
                                param.entity_type = entities_map[param.entity_type]
                                
                if 'transition_route_groups' in page:
                    temp_list = []
                    for trg in page.transition_route_groups:
                        temp_list.append(rgs_map[trg])

                        page.transition_route_groups = temp_list
                
                
        if agent_type == 'destination':
            intents_map = self.get_intents_map(agent_id, reverse=True)
            entities_map = self.get_entities_map(agent_id, reverse=True)
            webhooks_map = self.get_webhooks_map(agent_id, reverse=True)
            flows_map = self.get_flows_map(agent_id, reverse=True)
            pages_map = self.get_pages_map(flows_map[flow], reverse=True)
            rgs_map = self.get_route_groups_map(flows_map[flow], reverse=True)
            
            # For each page, recurse through the resources and look for
            # specific resource types that have been replaced with literal
            # string display_name. Perform a lookup using the map resources
            # and replace the str display_name with the appropriate str UUID
            
            for page in pages_mod:
                page.name = pages_map[page.display_name]

                if 'entry_fulfillment' in page:
                    if 'webhook' in page.entry_fulfillment:
                        page.entry_fulfillment.webhook = webhooks_map[page.entry_fulfillment.webhook]
                        
                if 'transition_routes' in page:
                    for tr in page.transition_routes:
                        if 'target_page' in tr:
                            if tr.target_page == 'END_FLOW':
                                tr.target_page = flows_map[flow] + '/pages/END_FLOW'
                                
                            elif tr.target_page == 'END_SESSION':
                                tr.target_page = flows_map[flow] + '/pages/END_SESSION'
                                
                            elif tr.target_page == 'CURRENT_PAGE':
                                tr.target_page = flows_map[flow] + '/pages/CURRENT_PAGE'
                                
                            else:
                                tr.target_page = pages_map[tr.target_page]

                        if 'intent' in tr:
                            tr.intent = intents_map[tr.intent]
                            if 'webhook' in tr.trigger_fulfillment:
                                tr.trigger_fulfillment.webhook = webhooks_map[tr.trigger_fulfillment.webhook]
                        elif 'condition' in tr and 'webhook' in tr.trigger_fulfillment:
                            tr.trigger_fulfillment.webhook = webhooks_map[tr.trigger_fulfillment.webhook]
                            
                if 'event_handlers' in page:
                    for handler in page.event_handlers:
                        if 'target_page' in handler:
                            if handler.target_page == 'END_FLOW':
                                handler.target_page = flows_map[flow] + '/pages/END_FLOW'
                                
                            elif handler.target_page == 'END_SESSION':
                                handler.target_page = flows_map[flow] + '/pages/END_SESSION'
                                
                            elif handler.target_page == 'CURRENT_PAGE':
                                handler.target_page = flows_map[flow] + '/pages/CURRENT_PAGE'
                                
                            else:
                                handler.target_page = pages_map[handler.target_page]
                                
                        if 'trigger_fulfillment' in handler:
                            if 'webhook' in handler.trigger_fulfillment:
                                handler.trigger_fulfillment.webhook = webhooks_map[handler.trigger_fulfillment.webhook]

                if 'form' in page:
                    if 'parameters' in page.form:
                        for param in page.form.parameters:
                            if 'fill_behavior' in param:
                                if 'initial_prompt_fulfillment' in param.fill_behavior:
                                    if 'webhook' in param.fill_behavior.initial_prompt_fulfillment:
                                        param.fill_behavior.initial_prompt_fulfillment.webhook = webhooks_map[param.fill_behavior.initial_prompt_fulfillment.webhook]
                                if 'reprompt_event_handlers' in param.fill_behavior:
                                    for handler in param.fill_behavior.reprompt_event_handlers:
                                        if 'trigger_fulfillment' in handler:
                                            if 'webhook' in handler.trigger_fulfillment:
                                                handler.trigger_fulfillment.webhook = webhooks_map[handler.trigger_fulfillment.webhook]
                                                
                                        if 'target_page' in handler:
                                            if handler.target_page == 'END_FLOW':
                                                handler.target_page = flows_map[flow] + '/pages/END_FLOW'
                                                
                                            elif handler.target_page == 'END_SESSION':
                                                handler.target_page = flows_map[flow] + '/pages/END_SESSION'
                                                
                                            elif handler.target_page == 'CURRENT_PAGE':
                                                handler.target_page = flows_map[flow] + '/pages/CURRENT_PAGE'
                                                
                                            else:
                                                handler.target_page = pages_map[handler.target_page]
                                        
                            if 'sys.' in param.entity_type:
                                pass
                            else:
                                param.entity_type = entities_map[param.entity_type]
                        
                if 'transition_route_groups' in page:
                    temp_list = []
                    for trg in page.transition_route_groups:
                        temp_list.append(rgs_map[trg])
                        
                    page.transition_route_groups = temp_list

        return pages_mod


    def convert_start_page_dependencies(self, agent_id, start_page, agent_type='source', flow='Default Start Flow'):
        page_mod = copy.deepcopy(start_page)

        if agent_type == 'source':
            intents_map = self.get_intents_map(agent_id)
            webhooks_map = self.get_webhooks_map(agent_id)
            flows_map = self.get_flows_map(agent_id, reverse=True)
            pages_map = self.get_pages_map(flows_map[flow])

            for tr in page_mod.transition_routes:
                if 'target_page' in tr:
                    if tr.target_page.split('/')[-1] == 'END_FLOW':
                        tr.target_page = 'END_FLOW'
                    elif tr.target_page.split('/')[-1] == 'START_PAGE':
                        tr.target_page = 'START_PAGE'
                    else:
                        tr.target_page = pages_map[tr.target_page]

                if 'intent' in tr:
                    tr.intent = intents_map[tr.intent]
                    if 'webhook' in tr.trigger_fulfillment:
                        tr.trigger_fulfillment.webhook = webhooks_map[tr.trigger_fulfillment.webhook]
                elif 'condition' in tr and 'webhook' in tr.trigger_fulfillment:
                    tr.trigger_fulfillment.webhook = webhooks_map[tr.trigger_fulfillment.webhook]

        if agent_type == 'destination':
            intents_map = self.get_intents_map(agent_id, reverse=True)
            webhooks_map = self.get_webhooks_map(agent_id, reverse=True)
            flows_map = self.get_flows_map(agent_id, reverse=True)
            pages_map = self.get_pages_map(flows_map[flow], reverse=True)

            for tr in page_mod.transition_routes:
                if 'target_page' in tr:
                    if tr.target_page == 'END_FLOW':
                        tr.target_page = flows_map[flow] + '/pages/END_FLOW'
                    elif tr.target_page == 'START_PAGE':
                        tr.target_page = flows_map[flow] + '/pages/START_PAGE'
                    else:
                        tr.target_page = pages_map[tr.target_page]

                if 'intent' in tr:
                    tr.intent = intents_map[tr.intent]
                    if 'webhook' in tr.trigger_fulfillment:
                        tr.trigger_fulfillment.webhook = webhooks_map[tr.trigger_fulfillment.webhook]
                elif 'condition' in tr and 'webhook' in tr.trigger_fulfillment:
                    tr.trigger_fulfillment.webhook = webhooks_map[tr.trigger_fulfillment.webhook]

        return page_mod
    
    
# PAGE FUNCTIONS
    def get_page_dependencies(self, obj_list):
        """ Pass in DFCX Page object(s) and retrieve all resource dependencies.
        
        Args:
            - obj_list, a List of one or more DFCX Page Objects
            
        Returns:
            - resources, Dictionary containing all of the resource objects
        """
        
        resources = defaultdict(list)
        
        temp_path = obj_list[0].name.split('/')
        flow_id = '/'.join(temp_path[0:8])
        route_groups = self.dfcx.list_transition_route_groups(flow_id)
        
        for page in obj_list:
            if 'entry_fulfillment' in page and 'webhook' in page.entry_fulfillment:
                resources['webhooks'].append(page.entry_fulfillment.webhook)
            if 'transition_routes' in page:
                for tr in page.transition_routes:
                    if 'intent' in tr:
                        resources['intents'].append(tr.intent)
                    elif 'condition' in tr and 'webhook' in tr.trigger_fulfillment:
                        resources['webhooks'].append(tr.trigger_fulfillment.webhook)
            if 'form' in page:
                if 'parameters' in page.form:
                    for param in page.form.parameters:
                        if 'sys.' in param.entity_type:
                            continue
                        else:
                            resources['entities'].append(param.entity_type)
                            
            if 'transition_route_groups' in page:
                for trg in page.transition_route_groups:
                    resources['route_groups'].append(trg)
                    for rg in route_groups:
                        if trg == rg.name:
                            for tr in rg.transition_routes:
                                resources['intents'].append(tr.intent)

        for key in resources:
            resources[key] = set(resources[key])
            
        return resources
    
        
### DATAFRAME FUNCTIONS

    def route_groups_to_dataframe(self, agent_id=None):
        """ This method extracts the Transition Route Groups from a given DFCX Agent 
        and returns key information about the Route Groups in a Pandas Dataframe
        
        DFCX Route Groups exist as an Agent level resource, however they are 
        categorized by the Flow they are associated with. This method will
        extract all Flows for the given agent, then use the Flow IDs to 
        extract all Route Groups per Flow. Once all Route Groups have been
        extracted, the method will convert the DFCX object to a Pandas
        Dataframe and return this to the user.
        
        Args:
          - agent_id, the Agent ID string in the following format:
            projects/<project_id>/locations/<location_id>/agents/<agent_id>
          
        Returns:
          - df, a Pandas Dataframe
        """
        
        if not agent_id:
            agent_id = self.agent_id
        
        # The following dicts and lists are setup to use to map "user friendly"
        # data labels before writing the Route Group object to a dataframe.
        flows_dict = {flow.display_name: flow.name for flow in self.dfcx.list_flows(agent_id)}
                
        intent_dict = {intent.name.split('/')[-1]:intent.display_name
                       for intent in self.dfcx.list_intents(agent_id)}
        
        webhooks_dict = {webhook.name.split('/')[-1]:webhook.display_name
                         for webhook in self.dfcx.list_webhooks(agent_id)}
                
        route_groups_dict = {flow:self.dfcx.list_transition_route_groups(flows_dict[flow]) for flow in flows_dict}

        rows_list = []
        for flow in route_groups_dict:
            for route_group in route_groups_dict[flow]:
                for route in route_group.transition_routes:
                    temp_dict = {}

                    temp_dict.update({'flow':flow})
                    temp_dict.update({'route_group_name':route_group.display_name})
                    temp_dict.update({'intent':intent_dict[route.intent.split('/')[-1]]})
                    
                    if route.trigger_fulfillment.webhook:temp_dict.update({'webhook':webhooks_dict[route.trigger_fulfillment.webhook.split('/')[-1]]})
                        
                    temp_dict.update({'webhook_tag':route.trigger_fulfillment.tag})
                    
                    if len(route.trigger_fulfillment.messages) > 0:
                        if len(route.trigger_fulfillment.messages[0].text.text) > 0:
                            temp_dict.update({'fulfillment_message':route.trigger_fulfillment.messages[0].text.text[0]})

                    rows_list.append(temp_dict)
                    
            
        df = pd.DataFrame(rows_list)
            
        return df

    def intents_to_dataframe(self,intents):
        """
        This functions takes an Intents object from the DFCX API and returns
        a Pandas Dataframe
        """
        intent_dict = defaultdict(list)

        for element in intents:
            if 'training_phrases' in element:
                for tp in element.training_phrases:
                    s = []
                    if len(tp.parts) > 1:
                        for item in tp.parts:
                            s.append(item.text)
                        intent_dict[element.display_name].append(''.join(s))
                    else:
                        intent_dict[element.display_name].append(tp.parts[0].text)
            else:
                intent_dict[element.display_name].append('')
                    
        df = pd.DataFrame.from_dict(intent_dict, orient='index').transpose()
        df = df.stack().to_frame().reset_index(level=1)
        df = df.rename(columns={'level_1':'intent',0:'tp'}).reset_index(drop=True)
        df = df.sort_values(['intent','tp'])

        return df

    
### SPECIAL PURPOSE FUNCTIONS
    def find_list_parameters(self,agent_id):
        """ This method extracts Parameters set at a page level that are 
        designated as "lists".
        
        Page level parameters are tied to Entity Types and can be returned
        as String or List types. If the user selects "list" at the page 
        level, the Entity Type will be returned with "is_list: True". This
        function will allow the user to provide an Agent ID and will return 
        all instances of parameters being used as lists on pages.
        
        Args:
          - agent_id, the Agent ID string in the following format:
            projects/<project_id>/locations/<location_id>/agents/<agent_id>
          
        Returns:
          - params_map, a Dict of parameter names and Pages they belong to
        """
        
        if not agent_id:
            agent_id = self.agent_id
        # entities = self.dfcx.list_entity_types(agent_id)
        flows_map = self.get_flows_map(agent_id)
        entities_map = self.get_entities_map(agent_id)

        params_list = []

        for flow in flows_map:
            temp_pages = self.dfcx.list_pages(flows_map[flow])
            for page in temp_pages:
                for param in page.form.parameters:
                    if param.is_list:
                        params_list.append(param.display_name)
                        print('FLOW = {}'.format(flow))
                        print('PAGE = {}'.format(page.display_name))
                        print(param.display_name)
                        if 'sys' in param.entity_type.split('/')[-1]:
                            print(param.entity_type.split('/')[-1])
                        else:
                            print(param.entity_type)
                            print(entities_map[param.entity_type.split('/')[-1]])
                        print('\n')

        return params_list
    
### EXPORT/IMPORT FUNCTIONS
    def export_flow(self, flow_id: str, gcs_path: str, data_format: str ='BLOB', ref_flows: bool =True) -> Dict[str, str]:
        """ Exports DFCX Flow(s) into GCS bucket.

        Args:
          flow_id, the formatted CX Flow ID to export
          gcs_path, the full GCS Bucket and File name path
          data_format, (Optional) One of 'BLOB' or 'JSON'. Defaults to 'BLOB'.
          ref_flows, (Optional) Bool to include referenced flows connected to primary flow

        Returns:
          lro, Dict with value containing a Long Running Operation UUID that can be
              used to retrieve status of LRO from dfcx.get_lro
        """
        base_url = 'https://dialogflow.googleapis.com/v3beta1'
        url = '{0}/{1}:export'.format(base_url, flow_id)
        body = {'flow_uri': '{}'.format(gcs_path), 'data_format': data_format, 'include_referenced_flows': ref_flows}
        token = subprocess.run(['gcloud', 'auth', 'application-default', 'print-access-token'],
                              stdout=subprocess.PIPE,
                              text=True).stdout

        token = token.strip('\n') # remove newline appended as part of stdout
        headers = {'Authorization': 'Bearer {}'.format(token), 'Content-Type': 'application/json; charset=utf-8'}

        # Make REST call
        r = requests.post(url, json=body, headers=headers)
        r.raise_for_status()

        lro = r.json()

        return lro
    
    def import_flow(self, agent_id: str, gcs_path: str, import_option: str = 'FALLBACK') -> Dict[str, str]:
        """ Imports a DFCX Flow from GCS bucket to CX Agent.

        Args:
          agent_id, the DFCX formatted Agent ID
          gcs_path, the full GCS Bucket and File name path
          import_option, one of 'FALLBACK' or 'KEEP'. Defaults to 'FALLBACK'

        Returns:
          lro, Dict with value containing a Long Running Operation UUID that can be
              used to retrieve status of LRO from dfcx.get_lro
        """

        base_url = 'https://dialogflow.googleapis.com/v3beta1'
        url = '{0}/{1}/flows:import'.format(base_url, agent_id)
        body = {'flow_uri': '{}'.format(gcs_path), 'import_option': '{}'.format(import_option)}
        token = subprocess.run(['gcloud', 'auth', 'application-default', 'print-access-token'],
                              stdout=subprocess.PIPE,
                              text=True).stdout

        token = token.strip('\n') # remove newline appended as part of stdout

        headers = {'Authorization': 'Bearer {}'.format(token), 'Content-Type': 'application/json; charset=utf-8'}

        # Make REST call
        r = requests.post(url, json=body, headers=headers)
        r.raise_for_status()

        lro = r.json()

        return lro
    
### LEGACY FUNCTIONS
    
class GitlabFunctions:
    def __init__(self):
        pass
        
    def gl_build_actions_list(self,action,file_list,content_path):
        actions_list = []

        if action in ['create','update']:
            for file in file_list:
                temp = {}
                temp['action'] = action
                temp['file_path'] = '/{}'.format(file)
                temp['content'] = open(content_path+'{}'.format(file)).read()

                actions_list.append(temp)

        elif action in ['delete']:
            for file in file_list:
                temp = {}
                temp['action'] = action
                temp['file_path'] = '/{}'.format(file)

                actions_list.append(temp)

        else:
            logging.info("You have entered an invalid action type: {}".format(action))

        return actions_list

    def gl_build_commit_data(self,actions_list,branch,message):
        data = {
            'branch': branch,
            'commit_message': message,
            'actions': actions_list
        }

        return data
