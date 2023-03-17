import os
import os.path
import shutil

from torchvision.datasets.utils import download_and_extract_archive
from torchvision.datasets.vision import VisionDataset

from typing import Union
from pathlib import Path
import numpy as np
from sklearn.model_selection import train_test_split

# Convert FGNet imports
import pandas as pd
from skimage.transform import resize
from skimage.io import imread, imsave
from skimage.util import img_as_ubyte
from tqdm import tqdm
import re

class FGNet(VisionDataset):
    def __init__(
        self, 
        root: Union[str, Path], 
        download: bool = False, 
        process_data: bool = True, 
        target_size: tuple = (128, 128), 
        categories: list = [3, 11, 16, 24, 40],
        test_size: float = 0.2,
        validation_size: float = 0.15
    ) -> None:
        
        '''
        FGNet dataset.
        
        Parameters
        ----------
        root : str or Path
            Root directory of dataset
        download : bool, optional
            If True, downloads the dataset from the internet and puts it in root directory. 
            If dataset is already downloaded, it is not downloaded again.
        process_data : bool, optional
            If True, processes the dataset and puts it in root directory.
            If dataset is already processed, it is not processed again.
        target_size : tuple, optional
            Size of the images after resizing.
        categories : list, optional
            List of categories to be used.
        test_size : float, optional
            Size of the test set.
        validation_size : float, optional
            Size of the validation set.
        '''
        
        super(FGNet, self).__init__(root)
        
        self.root = Path(self.root)
        self.root.parent.mkdir(parents=True, exist_ok=True)
        self.target_size = target_size
        self.categories = categories
        self.test_size = test_size
        self.validation_size = validation_size
            
        original_path = self.root / 'FGNET/images'
        processed_path = self.root / 'FGNET/data_processed'
        
        original_csv_path = self.root / 'FGNET/data_processed/fgnet.csv'
        train_csv_path = self.root / 'FGNET/data_processed/train.csv'
        test_csv_path = self.root / 'FGNET/data_processed/test.csv'
        
        original_images_path = self.root / 'FGNET/data_processed'
        train_images_path = self.root / 'FGNET/train'
        test_images_path = self.root / 'FGNET/test'
        
        if download:
            self.download()
        if not self._check_integrity_download():
            raise RuntimeError("Dataset not found or corrupted. You can use download=True to download it")
        
        if process_data:
            self.process(original_path, processed_path)
            self.split(original_csv_path, train_csv_path, test_csv_path, original_images_path, train_images_path, test_images_path)
    
    def download(self) -> None:
        if self._check_integrity_download():
            print("Files already downloaded and verified")
            return

        download_and_extract_archive(
            "http://yanweifu.github.io/FG_NET_data/FGNET.zip",
            self.root,
            filename="fgnet.zip",
            md5="1206978cac3626321b84c22b24cc8d19",
        )
        
    def process(self, original_path, processed_path):
        if self._check_integrity_process():
            print("Files already processed and verified")
            return
        
        data = self.load_data(original_path)
        df = pd.DataFrame(data, columns=['path', 'category'])
        processed_path.mkdir(parents=True, exist_ok=True)
        df.to_csv(processed_path / 'fgnet.csv', index=False)
        self.process_images_from_df(df, original_path, processed_path)
        return df
    
    def split(
        self, 
        original_csv_path, 
        train_csv_path, 
        test_csv_path, 
        original_images_path, 
        train_images_path, 
        test_images_path
    ):
        if self._check_integrity_split():
            print("Files already split and verified")
            return
        
        train, test = self.split_dataframe(
            original_csv_path,
            train_images_path, 
            original_images_path, 
            test_images_path
            )
        
        test.to_csv(test_csv_path, index=False)
        train.to_csv(train_csv_path, index=False)
        
    def _check_integrity_download(self) -> bool:
        return (self.root / "FGNET").exists()
    
    def _check_integrity_process_split(self) -> bool:
        return (self.root / "FGNET/data_processed").exists() and (self.root / "FGNET/trainval").exists() and (self.root / "FGNET/test").exists()
    
    def _check_integrity_process(self) -> bool:
        return (self.root / "FGNET/data_processed").exists()
    
    def _check_integrity_split(self) -> bool:
        return (self.root / "FGNET/train").exists() and (self.root / "FGNET/test").exists()
    
    def get_age_from_filename(self, filename):
        m = re.match("[0-9]+A([0-9]+).*", filename)
        return int(m.groups()[0])

    def find_category(self, real_age):
        for i, age in enumerate(self.categories):
            if real_age < age:
                return i
        return len(self.categories)
    
    def load_data(self, original_path):
        data = []
        for img in original_path.iterdir():
            age = self.get_age_from_filename(img.name)
            category = self.find_category(age)
            data.append([img.name, category])

        return data
    
    def process_images_from_df(self, df, original_path, processed_path):
        for idx, row in tqdm(df.iterrows(), total=df.shape[0], desc='Processing images', unit='image'):
            path = original_path / Path(row['path'])
            processed_path_images = processed_path / Path(row['path'])
            img = imread(path)
            img = img_as_ubyte(resize(img, self.target_size, anti_aliasing=True))
            
            processed_path_images.parent.mkdir(parents=True, exist_ok=True)
            imsave(processed_path_images, img, check_contrast=False)
            
    def split_dataframe(self, csv_path, train_images_path, original_images_path, test_images_path):
        df = pd.read_csv(csv_path)
        x = np.array(df['path'])
        y = np.array(df['category'])
        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=self.test_size, random_state=1)
        
        for path, label in zip(x_train, y_train):
            train_path = train_images_path / str(label)
            train_path.mkdir(parents=True, exist_ok=True)
            shutil.copy(original_images_path / path, train_path / path)

        for path, label in zip(x_test, y_test):
            test_path = test_images_path / str(label)
            test_path.mkdir(parents=True, exist_ok=True)
            shutil.copy(original_images_path / path, test_path / path)

        x_train, x_val, y_train, y_val = train_test_split(x_train, y_train, test_size=self.validation_size, random_state=1)

        train = np.hstack((x_train[:, np.newaxis], y_train[:, np.newaxis]))
        val = np.hstack((x_val[:, np.newaxis], y_val[:, np.newaxis]))
        test = np.hstack((x_test[:, np.newaxis], y_test[:, np.newaxis]))
        trainval = np.vstack((train, val))

        test_df = pd.DataFrame(data=test, columns=['path', 'category'])
        train_df = pd.DataFrame(data=trainval, columns=['path', 'category'])

        return train_df, test_df