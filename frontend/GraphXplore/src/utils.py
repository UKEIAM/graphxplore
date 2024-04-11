import streamlit as st
import pathlib
from typing import Any, Optional, List, Callable

ICON_PATH = str(pathlib.Path(__file__).parents[1].absolute() / 'graphxplore_icon.png')
BLOOM_PATH = str(pathlib.Path(__file__).parents[1].absolute() / 'bloom_config.json')
BROWSER_STYLE_PATH = str(pathlib.Path(__file__).parents[1].absolute() / 'browser_style.grass')

def get_how_to_image_path(image_name: str) -> str:
    return str(pathlib.Path(__file__).parents[1].absolute() / 'how_to_images' / (image_name + '.png'))

class VariableHandle:
    def __init__(self, var_key: str, init: Optional[Any]=None):
        self.var_key = var_key
        if self.var_key not in st.session_state:
            st.session_state[self.var_key] = init

    def get_attr(self) -> Any:
        return st.session_state[self.var_key]

    def set_attr(self, val: Any):
        st.session_state[self.var_key] = val


class ListHandle:
    def __init__(self, list_key: str, init: Optional[List[Any]] = None):
        self.list_key = list_key
        if self.list_key not in st.session_state:
            st.session_state[self.list_key] = init if init else []

    def append(self, element: Any):
        st.session_state[self.list_key].append(element)

    def reset(self):
        del st.session_state[self.list_key][1:]

    def pop(self):
        st.session_state[self.list_key].pop()

    def remove(self, element: Any):
        st.session_state[self.list_key].remove(element)

    def set_list(self, to_set: List[Any]):
        st.session_state[self.list_key] = to_set

    def get_list(self):
        return st.session_state[self.list_key]

class FunctionWrapper:
    @staticmethod
    def wrap_func(parent_obj, success_message: Optional[str], func: Callable, *args: Any):
        try:
            func(*args)
            if success_message:
                parent_obj.success(success_message)
        except AttributeError as err:
            parent_obj.error('ERROR: ' + str(err))
