import csv
import io
import streamlit as st
from io import StringIO, BytesIO
import zipfile
import chardet
from typing import Optional, List, Any, Dict
from graphxplore.MetaDataHandling import MetaData

class CSVUploader:
    def __init__(self, table_data_store_location: str, upload_text: str, upload_help: Optional[str]= None,
                 required_tables: Optional[List[str]]= None, accept_multiple_files: bool = True,
                 key: Optional[str]= None):
        self.required_tables = required_tables if required_tables else []
        self.upload_text = upload_text
        self.upload_help = upload_help
        self.key = key
        self.accept_multiple_files = accept_multiple_files
        self.table_data_store_location = table_data_store_location
        if table_data_store_location not in st.session_state:
            st.session_state[table_data_store_location] = {}

    def _upload_data(self, cont, uploaded_files, file_enc, delimiter):
        if uploaded_files is None or (self.accept_multiple_files and len(uploaded_files) == 0):
            cont.error('ERROR: You have to select CSV files before uploading')
        else:
            files = uploaded_files if self.accept_multiple_files else [uploaded_files]
            missing_tables = []
            file_names = [file.name.replace('.csv', '') for file in files]
            for req_table in self.required_tables:
                if req_table not in file_names:
                    missing_tables.append(req_table)
            if len(missing_tables) > 0:
                cont.error('ERROR: Following tables are missing from upload: "' + '", "'.join(missing_tables) + '"')
            else:
                try:
                    loaded_data = {}
                    for file in files:
                        raw_bytes = file.getvalue()
                        table_name = file.name.replace('.csv', '')
                        if file_enc == 'auto':
                            enc = chardet.detect(raw_bytes)['encoding']
                            # ascii (without special characters) is subset of utf-8
                            if enc == 'ascii' or enc == 'utf-8':
                                enc = 'utf-8-sig'
                        else:
                            enc = file_enc
                        csv_str = raw_bytes.decode(enc)
                        str_file = StringIO(csv_str)
                        if delimiter == 'auto':
                            try:
                                dialect = csv.Sniffer().sniff(str_file.read(100000), delimiters=',;|\t ')
                                str_file.seek(0)
                                reader = csv.DictReader(str_file, dialect=dialect)
                            except csv.Error:
                                str_file.seek(0)
                                reader = csv.DictReader(str_file)
                        else:
                            reader = csv.DictReader(str_file, delimiter=delimiter)
                        loaded_data[table_name] = [line for line in reader]

                    st.session_state[self.table_data_store_location] = loaded_data
                except AttributeError as e:
                    cont.error('ERROR: ' + str(e))

    def render(self, parent_obj: Optional[Any] = None):
        cont = st.container() if parent_obj is None else parent_obj.container()
        file_enc_col, delimiter_col = cont.columns(2)
        file_enc = file_enc_col.selectbox(label='File encoding',
                                          options=['auto', 'utf-8-sig', 'utf-8', 'ascii', 'ISO-8859-1'],
                                          key=self.key + '_enc' if self.key else None,
                                          help='Select file encoding of CSV files or detect automatically (default)')
        delimiter = delimiter_col.selectbox('Delimiter', options=['auto', ',', ';', '|', '\t'],
                                            key=self.key + '_del' if self.key else None,
                                            help='Select CSV delimiter or detect automatically (default)')
        uploaded_files = cont.file_uploader(self.upload_text, type='csv',
                                            accept_multiple_files=self.accept_multiple_files, key=self.key,
                                            help=self.upload_help)

        st.button('Upload data', key=self.key + '_button' if self.key else None,
                  help='Will overwrite all previously uploaded CSV files', on_click=self._upload_data,
                  args=[cont, uploaded_files, file_enc, delimiter])

class CSVDownloader:
    def __init__(self, data_store_location: str, download_text: str, file_name: str, download_help: Optional[str]=None,
                 key: Optional[str]= None):
        self.data_store_location = data_store_location
        if data_store_location not in st.session_state:
            st.session_state[self.data_store_location] = {}
        self.download_text = download_text
        self.file_name = file_name
        self.download_help = download_help
        self.key = key

    @staticmethod
    def _create_zip(_parent_obj, data_to_zip: Dict[str, List[Dict[str, str]]], encoding: str, delimiter: str):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, mode='a') as zip_file:
            for table, table_data in data_to_zip.items():
                csv_data = CSVDownloader._create_csv(_parent_obj, table_data, encoding, delimiter)
                if len(csv_data) == 0:
                    return b''
                zip_file.writestr(table + '.csv', csv_data)
        return zip_buffer.getvalue()

    @staticmethod
    def _create_csv(_parent_obj, data_to_zip: List[Dict[str, str]], encoding: str, delimiter: str):
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=data_to_zip[0].keys(), delimiter=delimiter)
        writer.writeheader()
        writer.writerows(data_to_zip)
        try:
            return csv_buffer.getvalue().encode(encoding)
        except UnicodeEncodeError as err:
            _parent_obj.error('ERROR:' + (str(err)))
            return b''

    def render(self, parent_obj: Optional[Any] = None):
        cont = st.container() if parent_obj is None else parent_obj.container()
        file_enc_col, delimiter_col = cont.columns(2)
        file_enc = file_enc_col.selectbox(label='File encoding',
                                          options=['utf-8', 'utf-8-sig', 'ISO-8859-1'],
                                          key=self.key + '_enc' if self.key else None,
                                          help='Select file encoding of CSV files')
        delimiter = delimiter_col.selectbox('Delimiter', options=[',', ';', '|', '\t'],
                                            key=self.key + '_del' if self.key else None)


        stored_data = st.session_state[self.data_store_location]

        if len(stored_data) > 1:
            data_to_download = self._create_zip(cont, stored_data, file_enc, delimiter)
            name_with_ext = self.file_name + '.zip'
        else:
            data_to_download = self._create_csv(cont, next(iter(stored_data.values())), file_enc, delimiter)
            name_with_ext = next(iter(stored_data.keys())) + '.csv'
        cont.download_button(self.download_text, data=data_to_download, file_name=name_with_ext,
                             mime='application/zip' if len(stored_data) > 1 else 'text/csv',
                             disabled=len(stored_data) == 0 or len(data_to_download) == 0)
