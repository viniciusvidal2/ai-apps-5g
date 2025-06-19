import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import numpy as np
import io


class NeuralNetworkTrainer:
    def __init__(self) -> None:
        """Initializes a NeuralNetworkTrainer object to handle training and prediction tasks for a neural network model."""
        self.input_data = None
        self.output_data = None
        self.model = None
        self.device = torch.device(
            'cuda' if torch.cuda.is_available() else 'cpu')
        self.input_size = None
        self.output_size = None
        self.hidden_layers = None

    def set_data(self, input_dict: dict, output_dict: dict) -> None:
        """Set input and output data for the neural network.

        Args:
            input_dict (dict): Dictionary where keys are feature names and values are lists of feature values.
            output_dict (dict): Dictionary where keys are target names and values are lists of target values.
        """
        # Convert dicts to ordered lists
        input_array = np.column_stack([input_dict[key] for key in input_dict])
        output_array = np.column_stack(
            [output_dict[key] for key in output_dict])
        assert input_array.shape[0] == output_array.shape[0], "Input and output must have the same number of samples"
        # The sizes of input and output data
        self.input_size = input_array.shape[1]
        self.output_size = output_array.shape[1]
        # Scale and set type for the data
        self.scaler_in = StandardScaler()
        self.scaler_out = StandardScaler()
        input_scaled = self.scaler_in.fit_transform(input_array)
        output_scaled = self.scaler_out.fit_transform(output_array)
        self.input_data = input_scaled.astype(np.float32)
        self.output_data = output_scaled.astype(np.float32)

    def set_network_shape(self, hidden_layers: list) -> None:
        """Set the architecture of the neural network.

        Args:
            hidden_layers (list): List of integers where each integer represents the number of neurons in a hidden layer.
        """
        self.hidden_layers = hidden_layers

    def build_model(self) -> None:
        """Build a fully connected feedforward neural network with the specified architecture.
        """
        if self.input_size is None or self.output_size is None or self.hidden_layers is None:
            raise ValueError(
                "Data and network shape must be set before building the model.")
        layers = []
        # Input to first hidden
        in_features = self.input_size
        for hidden in self.hidden_layers:
            layers.append(nn.Linear(in_features, hidden))
            layers.append(nn.ReLU())
            in_features = hidden
        # Last hidden to output
        layers.append(nn.Linear(in_features, self.output_size))
        # Output sequential model
        self.model = nn.Sequential(*layers).to(self.device)

    def prepare_dataloaders(self, batch_size: int = 32) -> tuple:
        """ Prepare DataLoaders for training, validation, and testing.

        Args:
            batch_size (int): The batch size for the DataLoader.

        Returns:
            tuple: A tuple containing the train, validation, and test DataLoaders.
        """
        # Split the data into train, validation, and test sets
        # 70% train, 15% val, 15% test
        X = self.input_data
        y = self.output_data
        X_train, X_temp, y_train, y_temp = train_test_split(
            X, y, test_size=0.3, random_state=42)
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.5, random_state=42)
        # Create TensorDatasets
        train_ds = TensorDataset(torch.tensor(X_train), torch.tensor(y_train))
        val_ds = TensorDataset(torch.tensor(X_val), torch.tensor(y_val))
        test_ds = TensorDataset(torch.tensor(X_test), torch.tensor(y_test))
        train_loader = DataLoader(
            train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size)
        test_loader = DataLoader(test_ds, batch_size=batch_size)
        return train_loader, val_loader, test_loader

    def train(self, epochs: int = 100, lr: float = 0.001, batch_size: int = 32):
        """Train the neural network model.

        Args:
            epochs (int): Number of training epochs.
            lr (float): Learning rate for the optimizer.
            batch_size (int): Batch size for the DataLoader.

        Raises:
            ValueError: If the model has not been built before training.
        """
        # Get everything ready for training
        if self.model is None:
            self.build_model()
        train_loader, val_loader, test_loader = self.prepare_dataloaders(
            batch_size)
        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=lr)
        # Train for as many epochs as specified
        for epoch in range(epochs):
            self.model.train()
            train_loss = 0.0
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(
                    self.device), targets.to(self.device)
                # Zero the gradients, forward pass, compute loss, backward pass, and update weights
                optimizer.zero_grad()
                outputs = self.model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                train_loss += loss.item() * inputs.size(0)
            train_loss /= len(train_loader.dataset)
            val_loss = self.evaluate(val_loader, criterion)
            print(
                f"Epoch {epoch + 1}/{epochs} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")
        test_loss = self.evaluate(test_loader, criterion)
        print(f"Test Loss: {test_loss:.4f}")

    def evaluate(self, loader: DataLoader, criterion: nn.modules.loss) -> float:
        """Evaluate the model on a given DataLoader.

        Args:
            loader (DataLoader): DataLoader for the dataset to evaluate.
            criterion (nn.modules.loss): Loss function to compute the loss.

        Returns:
            float: The average loss over the dataset.
        """
        self.model.eval()
        total_loss = 0.0
        # Disable gradient calculation for evaluation
        with torch.no_grad():
            for inputs, targets in loader:
                inputs, targets = inputs.to(
                    self.device), targets.to(self.device)
                outputs = self.model(inputs)
                loss = criterion(outputs, targets)
                total_loss += loss.item() * inputs.size(0)
        # Average the loss over the dataset
        total_loss /= len(loader.dataset)
        return total_loss

    def predict(self, input_dict: dict) -> np.ndarray:
        """Make predictions using the trained model.

        Args:
            input_dict (dict): Dictionary where keys are feature names and values are lists of feature values.
        
        Returns:
            np.ndarray: The predicted output values after inverse scaling.
        """
        # Prepare the input data for prediction
        input_array = np.column_stack([input_dict[key] for key in input_dict])
        input_scaled = self.scaler_in.transform(input_array.astype(np.float32))
        # Convert to tensor and move to the appropriate device
        input_tensor = torch.tensor(
            input_scaled, dtype=torch.float32).to(self.device)
        # Ensure the model is in evaluation mode and make predictions
        self.model.eval()
        with torch.no_grad():
            output_tensor = self.model(input_tensor)
        # Move the output tensor back to CPU and inverse transform it
        output_scaled = output_tensor.cpu().numpy()
        output = self.scaler_out.inverse_transform(output_scaled)
        return output
    
    def get_serialized_model(self) -> bytes:
        """Get the trained model.

        Returns:
            bytes: The serialized trained neural network model.
        """
        buffer = io.BytesIO()
        torch.save(self.model.state_dict(), buffer)
        return buffer.getvalue()


if __name__ == "__main__":
    # Example dummy data
    input_data = {
        "feature1": list(np.random.rand(200)),
        "feature2": list(np.random.rand(200)),
    }
    output_data = {
        "target": list(2 * np.array(input_data["feature1"]) + 3 * np.array(input_data["feature2"]) + np.random.randn(200) * 0.1)
    }

    trainer = NeuralNetworkTrainer()
    trainer.set_data(input_data, output_data)
    # 2 hidden layers with 32 and 16 neurons
    trainer.set_network_shape(hidden_layers=[32, 16])
    trainer.build_model()
    trainer.train(epochs=100, lr=0.01, batch_size=16)

    # Prediction example
    new_input = {
        "feature1": [0.5],
        "feature2": [0.8],
    }
    prediction = trainer.predict(new_input)
    print("Prediction:", prediction)
