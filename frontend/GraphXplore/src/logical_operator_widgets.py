import streamlit as st
from typing import List, Optional, Tuple
from enum import Enum
from .utils import ListHandle
from graphxplore.MetaDataHandling import MetaData, DataType
from graphxplore.DataMapping import AggregatorType
from graphxplore.DataMapping.Conditionals import *

class ConditionEdit(str, Enum):
    NewBlock = 'NEW'
    StartAtomic = 'ATOMICSTART'
    CommonAtomic = 'ATOMICCOMMON'
    AggAtomic = 'ATOMICAGG'
    ContainAtomic = 'ATOMICCONTAIN'
    StringAtomic = 'ATOMICSTRING'
    IntAtomic = 'ATOMICINT'
    FloatAtomic = 'ATOMICFLOAT'
    ListAtomic = 'ATOMICLIST'

class ConditionDefinition:
    def __init__(self, condition_history_location: str, source_meta: MetaData, source_tables_for_single: List[str],
                 source_tables_for_agg: List[str], history_init: Optional[List[Tuple[str, ConditionEdit]]]=None,
                 for_mapping: bool = True, key: Optional[str] = None):
        if condition_history_location not in st.session_state:
            st.session_state[condition_history_location] = history_init if history_init else [(':red[<placeholder>]', ConditionEdit.NewBlock)]
        self.condition_history_location = condition_history_location
        self.source_meta = source_meta
        self.source_tables_for_single = source_tables_for_single
        self.source_tables_for_agg = source_tables_for_agg
        self.last_state, self.last_edit = st.session_state[condition_history_location][-1]
        self.updated_condition = None
        self.new_last_edit = None
        self.history_handle = ListHandle(self.condition_history_location)
        self.for_mapping = for_mapping
        self.key = key

    def _get_selection_container(self, parent_obj):
        cont = parent_obj.container()
        if self.last_edit == ConditionEdit.NewBlock:
            block_type = cont.selectbox('Choose type of condition for red block', ['Atomic', 'And', 'Or', 'Negated'],
                                        key=self.key + '_new_block_select' if self.key else None)
            if block_type == 'And' or block_type == 'Or':
                nof_sub_blocks = cont.slider('Choose number of conditions to concatenate', 2, 10, 2,
                                             key=self.key + '_concat' if self.key else None)
                sub_blocks = ['<placeholder>' for idx in range(nof_sub_blocks)]
                sub_blocks[0] = ':red[<placeholder>]'
                self.updated_condition = '(' + (' AND ' if block_type == 'And' else ' OR ').join(sub_blocks) + ')'
                self.new_last_edit = ConditionEdit.NewBlock
            elif block_type == 'Negated':
                self.updated_condition = '(NOT :red[<placeholder>])'
                self.new_last_edit = ConditionEdit.NewBlock
            # atomic
            else:
                self.updated_condition = '(:red[<placeholder>])'
                self.new_last_edit = ConditionEdit.StartAtomic
        elif self.last_edit == ConditionEdit.StartAtomic:
            if len(self.source_tables_for_agg) > 0:
                atomic_options = ['Single', 'Aggregation', 'Always true']
            else:
                atomic_options = ['Single', 'Always true']
            if self.for_mapping:
                start_atomic_help = ('This target table is associated with some (or multiple) table(s) x of the source '
                                     'dataset. Variables of x or foreign source tables of x (or '
                                     'foreign table chains) can be used for single value conditions. '
                                     'Variables of source tables which have x as an foreign table '
                                     '(or inverted foreign table chains) can be used for aggregation '
                                     'conditions. The "TRUE" operator always evaluates to true')
            else:
                start_atomic_help = ('Variables of the table for group members or foreign tables (or '
                                      'foreign table chains) can be used for single value filter conditions. '
                                      'Variables of tables which have the group member table as an '
                                      'foreign table (or inverted foreign table chains) can be used for '
                                      'aggregation filter conditions. The "TRUE" operator always '
                                      'evaluates to true and can be used if all primary keys of a table '
                                      'should be group members')
            agg_sing_type = cont.selectbox(
                'Choose between tautology, single value or aggregation of data statements for red block',
                atomic_options,
                help=start_atomic_help, key=self.key + '_single_atomic_select' if self.key else None)
            if agg_sing_type == 'Single':
                self.updated_condition = ':red[<placeholder>]'
                self.new_last_edit = ConditionEdit.CommonAtomic
            elif agg_sing_type == 'Aggregation':
                self.updated_condition = 'AGGREGATE :red[<placeholder>]'
                self.new_last_edit = ConditionEdit.AggAtomic
            else:
                self.updated_condition = 'TRUE'
                self.new_last_edit = ConditionEdit.NewBlock
        elif self.last_edit == ConditionEdit.AggAtomic:
            agg_col, table_col, var_col, data_type_col = cont.columns(4)
            agg_type_sel = agg_col.selectbox('Choose aggregation type for red block', AggregatorType.__members__,
                                             help='List all aggregated values and check for element containment, count '
                                                  'aggregated values, or concatenate aggregated values joined by semicolons. '
                                                  'For aggregated numeric values the sum, min, max, mean, '
                                                  'standard deviation, median or amplitude (max - min) can be calculated '
                                                  'and compared against',
                                             key=self.key + '_agg_single_select' if self.key else None)
            agg_type = AggregatorType._member_map_[agg_type_sel]
            table_cond = table_col.selectbox('Choose source table for aggregation', self.source_tables_for_agg,
                                             key=self.key + '_table_agg_select' if self.key else None)
            var_cond = var_col.selectbox('Choose source variable for aggregation',
                                         self.source_meta.get_variable_names(table_cond),
                                         key=self.key + '_var_agg_select' if self.key else None)
            var_cond_data_type = self.source_meta.get_variable(table_cond, var_cond).data_type
            if agg_type in [AggregatorType.Min, AggregatorType.Max, AggregatorType.Mean, AggregatorType.Sum,
                            AggregatorType.Std, AggregatorType.Median, AggregatorType.Amplitude]:
                numeric_types = [DataType.Integer.value, DataType.Decimal.value]
                data_type_options = [var_cond_data_type.value] + [entry for entry in numeric_types if
                                                                  entry != var_cond_data_type.value] if var_cond_data_type in numeric_types else numeric_types
            else:
                data_type_options = [var_cond_data_type.value] + [entry for entry in
                                                                  DataType.__members__ if
                                                                  entry != var_cond_data_type.value]
            data_type_cond = data_type_col.selectbox('Choose data type for aggregation', data_type_options,
                                                     help='Source variable values that do not match this data type '
                                                          'are not aggregated',
                                                     key=self.key + '_agg_data_type_select' if self.key else None)
            self.updated_condition = agg_type.value + ' VARIABLE ' + var_cond + ' OF TYPE ' + data_type_cond + ' IN TABLE ' + table_cond + ' :red[<placeholder>]'
            if agg_type == AggregatorType.List:
                self.new_last_edit = ConditionEdit.ContainAtomic
            elif agg_type == AggregatorType.Concatenate:
                self.new_last_edit = ConditionEdit.StringAtomic
            elif agg_type == AggregatorType.Count:
                self.new_last_edit = ConditionEdit.IntAtomic
            else:
                self.new_last_edit = ConditionEdit.FloatAtomic
        elif self.last_edit == ConditionEdit.CommonAtomic:
            table_col, var_col, data_type_col = cont.columns(3)
            table_cond = table_col.selectbox('Choose source table for red block', self.source_tables_for_single,
                                             key=self.key + '_atomic_sing_table' if self.key else None)
            var_cond = var_col.selectbox('Choose source variable for red block',
                                          self.source_meta.get_variable_names(table_cond),
                                          key=self.key + '_atomic_sing_var' if self.key else None)
            var_cond_data_type = self.source_meta.get_variable(table_cond, var_cond).data_type
            data_type_options = [var_cond_data_type.value] + [entry for entry in
                                                              DataType.__members__ if
                                                              entry != var_cond_data_type.value]
            data_type_cond = data_type_col.selectbox('Choose data type for red block', data_type_options,
                                                     help='Source variable values that do not match this data type '
                                                          'automatically do not meet the condition of this atomic '
                                                          'conditional block',
                                                     key=self.key + '_atomic_sing_data_type' if self.key else None)
            self.updated_condition = 'VARIABLE ' + var_cond + ' OF TYPE ' + data_type_cond + ' IN TABLE ' + table_cond + ' :red[<placeholder>]'
            self.new_last_edit = (ConditionEdit.StringAtomic
                                  if DataType._value2member_map_[data_type_cond] == DataType.String
                                  else ConditionEdit.IntAtomic if DataType._value2member_map_[
                                                                      data_type_cond] == DataType.Integer
            else ConditionEdit.FloatAtomic)
        elif self.last_edit == ConditionEdit.ContainAtomic:
            check_val = cont.text_input('Insert string to check for existence in list of aggregated values',
                                        key=self.key + '_list_val_input' if self.key else None)
            self.updated_condition = StringOperatorType.Contains.value + ' "' + check_val + '"'
            self.new_last_edit = ConditionEdit.NewBlock
        elif self.last_edit == ConditionEdit.StringAtomic:
            comp_col, val_col = cont.columns(2)
            compare_select = comp_col.selectbox('Choose comparison', ['Equals', 'Contains', 'In List'],
                                                help='Choose between checking the variable values for equality, '
                                                     'substring containment, or presence in a list of strings',
                                                key=self.key + '_str_compare' if self.key else None)
            if compare_select != 'In List':
                comp_string = StringOperatorType.Equals.value if compare_select == 'Equals' else StringOperatorType.Contains.value
                check_val = val_col.text_input('Insert string to check against',
                                                key=self.key + '_str_compare_val' if self.key else None)
                self.updated_condition = comp_string + ' "' + check_val + '"'
                self.new_last_edit = ConditionEdit.NewBlock
            else:
                self.updated_condition = 'IN [:red[<placeholder>]]'
                self.new_last_edit = ConditionEdit.ListAtomic

        elif self.last_edit == ConditionEdit.IntAtomic or self.last_edit == ConditionEdit.FloatAtomic:
            comp_col, val_col = cont.columns(2)
            compare_select = comp_col.selectbox('Choose comparison', ['==', '<', '>', '<=', '>=', 'In List'],
                                                help='Choose between checking the relation of variable values to a '
                                                     'comparison value, or their presence in a list of strings',
                                                key=self.key + '_num_compare' if self.key else None)
            if compare_select != 'In List':
                def_num_val = 0 if self.last_edit == ConditionEdit.IntAtomic else 0.0
                check_val = val_col.number_input('Insert numeric value to check against', value=def_num_val,
                                                 key=self.key + '_num_compare_val' if self.key else None)
                self.updated_condition = compare_select + ' ' + str(check_val)
                self.new_last_edit = ConditionEdit.NewBlock
            else:
                self.updated_condition = 'IN [:red[<placeholder>]]'
                self.new_last_edit = ConditionEdit.ListAtomic

        elif self.last_edit == ConditionEdit.ListAtomic:
            list_empty = '[:red[<placeholder>]]' in self.last_state
            list_act_options = ['Add list item'] if list_empty else ['Add list item', 'Finish list']
            select_col, val_col = cont.columns(2)
            list_act_select = select_col.selectbox('Choose action for string list', list_act_options,
                                                    key=self.key + '_list_edit' if self.key else None)
            if list_act_select == 'Add list item':
                add_val = val_col.text_input('Insert string to check against',
                                             key=self.key + '_list_edit_val' if self.key else None)
                if ',' in add_val:
                    cont.error('List item cannot contain comma')
                self.updated_condition = '' if list_empty else ', '
                if ' ' in add_val or add_val == '':
                    self.updated_condition += '"' + add_val + '":red[<placeholder>]'
                else:
                    self.updated_condition += add_val + ':red[<placeholder>]'
                self.new_last_edit = ConditionEdit.ListAtomic
            else:
                self.updated_condition = ''
                self.new_last_edit = ConditionEdit.NewBlock
        else:
            raise NotImplementedError('State ' + self.last_edit.value() + ' not implemented')

    def _add_current_state(self):
        condition_history_state = self.last_state.replace(':red[<placeholder>]', self.updated_condition, 1)
        if ':red[<placeholder>]' not in condition_history_state:
            condition_history_state = condition_history_state.replace('<placeholder>', ':red[<placeholder>]', 1)
        self.history_handle.append((condition_history_state, self.new_last_edit))
        self.last_state, self.last_edit = st.session_state[self.condition_history_location][-1]

    def render(self, parent_obj):
        cont = parent_obj.container()
        history_handle = ListHandle(self.condition_history_location)
        undo_col, reset_col = cont.columns(2)
        undo_col.button('Undo', disabled=len(st.session_state[self.condition_history_location]) < 2,
                        key=self.condition_history_location + '_undo',
                        on_click=history_handle.pop)
        reset_col.button('Fully reset statement', disabled=len(st.session_state[self.condition_history_location]) < 2,
                         type='primary', key=self.condition_history_location + '_reset', on_click=history_handle.reset)
        if '<placeholder>' not in self.last_state:
            cont.success('Finished statement')
        else:
            self._get_selection_container(cont)
            cont.button('Ok', key=self.condition_history_location + '_condition_creation_okay',
                        on_click=self._add_current_state)