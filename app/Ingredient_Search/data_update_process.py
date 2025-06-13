from pdf_data_read import pdf_data_read_main
from bjsp_download_process import download_all

def main():
    download_all()
    pdf_data_read_main()

if __name__ == '__main__':
    main()