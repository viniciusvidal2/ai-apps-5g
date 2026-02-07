import io
import pandas as pd
import base64


class SheetDataSelection:
    """Handles the selection of data from a spreadsheet.
    This class will test the data selection capabilities by extracting data from a spreadsheet,
    and then sending input and output data for a neural network model to process.
    """

    def __init__(self) -> None:
        """Initializes a SheetDataSelection object to handle spreadsheet data selection tasks.
        """
        self.sheet_data = None  # DataFrame to hold the spreadsheet data
        self.input_columns = []
        self.output_columns = []
        # Dictionary to hold the selected input and output data
        self.selected_data = {"input": [], "output": []}

    def set_sheet_data(self, data: str, sheet_name: str) -> None:
        """Sets the spreadsheet data from a base64 encoded string.

        Args:
            data (str): The base64 encoded string representing the spreadsheet data.
            sheet_name (str): The name of the sheet to be processed.
        """
        sheet_data_bytes = base64.b64decode(data)
        # Decode based on the file extension
        if sheet_name.endswith('.xlsx'):
            self.sheet_data = pd.read_excel(io.BytesIO(
                sheet_data_bytes), sheet_name=sheet_name)
        elif sheet_name.endswith('.csv'):
            # If the sheet is a CSV, read it directly
            self.sheet_data = pd.read_csv(
                io.BytesIO(sheet_data_bytes), encoding='utf-8')
        else:
            raise ValueError(
                "Unsupported file format. Only .xlsx and .csv are supported.")

    def set_input_data_collumns(self, input_columns: list[str]) -> None:
        """Sets the input columns for the spreadsheet data selection.

        Args:
            input_columns (list[str]): The list of input column names to be used for selection.
        """
        self.input_columns = input_columns

    def set_output_data_collumns(self, output_columns: list[str]) -> None:
        """Sets the output columns for the spreadsheet data selection.

        Args:
            output_columns (list[str]): The list of output column names to be used for selection.
        """
        self.output_columns = output_columns

    def select_data(self) -> None:
        """Selects data from the spreadsheet based on the given criteria.
        """
        self.selected_data = {"input": [], "output": []}
        # Make sure we have valid columns to select
        valid_inputs = [
            col for col in self.input_columns if col in self.sheet_data.columns]
        valid_outputs = [
            col for col in self.output_columns if col in self.sheet_data.columns]
        # Update the input and output columns with valid ones
        if self.sheet_data is not None:
            if self.input_columns:
                self.selected_data["input"] = self.sheet_data[valid_inputs].to_dict(
                    orient='list')
            if self.output_columns:
                self.selected_data["output"] = self.sheet_data[valid_outputs].to_dict(
                    orient='list')
        else:
            raise ValueError(
                "Sheet data is not set. Please set the sheet data before selecting.")

    def get_selected_data(self) -> dict:
        """Returns the selected data from the spreadsheet.

        Returns:
            dict: The selected data.
        """
        if self.selected_data["input"] == [] and self.selected_data["output"] == []:
            self.select_data()
        return self.selected_data


if __name__ == "__main__":
    # Example usage of the SheetDataSelection class
    sheet_data_selection = SheetDataSelection()
    # Simulating setting sheet data from a base64 encoded CSV string
    file_path = "/home/vini/Documents/test.csv"
    with open(file_path, "rb") as f:
        file_bytes = f.read()
        example_data = base64.b64encode(file_bytes).decode('utf-8')
        sheet_data_selection.set_sheet_data(data=example_data, sheet_name='test.csv')
        sheet_data_selection.set_input_data_collumns(input_columns=['x', 'y'])
        sheet_data_selection.set_output_data_collumns(output_columns=['z'])
        # Output should show the selected input and output data based on the specified columns.
        sheet_data_selection.select_data()
        selected_data = sheet_data_selection.get_selected_data()
        print("Selected Input Data:", selected_data["input"])
        print("Selected Output Data:", selected_data["output"])
