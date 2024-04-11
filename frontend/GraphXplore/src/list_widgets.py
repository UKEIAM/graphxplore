import streamlit as st
from .utils import ListHandle
from typing import Optional, Any, List

class EditableList:
    def __init__(self, list_key: str, init: Optional[List[str]] = None, list_help: Optional[str] = None):
        self.list_key = list_key
        self.handle = ListHandle(list_key, init)
        self.list_help = list_help

    def _add_item(self, parent_obj, entry: str):
        if entry in st.session_state[self.list_key]:
            parent_obj.error(entry + ' already exists in list')
        else:
            self.handle.append(entry)

    def render(self, parent_obj: Optional[Any] = None):
        cont = st.container() if parent_obj is None else parent_obj.container()
        if self.list_help is not None:
            if cont.checkbox('Show tooltip', key=self.list_key + '_tooltip'):
                cont.markdown(self.list_help)

        add_key = self.list_key + '_add_text'
        cont.text_input('Insert item to add', key=add_key,
                        on_change=lambda: self._add_item(cont, st.session_state[add_key]))

        cols = cont.columns(2)

        for idx in range(len(st.session_state[self.list_key])):
            entry = st.session_state[self.list_key][idx]
            clean_entry = (entry if entry.strip() != '' else '"' + entry + '" (empty string)' if entry == ''
                else '"' + entry + '" (' + str(entry.count(' ')) + ' whitespaces)')
            cols[idx % 2].button(clean_entry, help='Click to remove', on_click=lambda x : self.handle.remove(x),
                                 args=[entry], key=self.list_key + '_' + entry)