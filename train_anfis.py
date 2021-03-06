import torch
import argparse
import load_model
import experimental
import numpy as np
import pickle as pkl
from membership import make_anfis
from sklearn.model_selection import train_test_split
from torch.utils.data import TensorDataset, DataLoader
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler

def get_args():
    parser = argparse.ArgumentParser("FOX code for regression tasks")
    parser.add_argument("-s", "--seed", type=int, default=123, help="seed value for torch, numpy")
    parser.add_argument("-d", "--dataset_name", type=str, default="sepsis_cases_1", help="dataset name")
    parser.add_argument("-t", "--task", type=str, default='classification',
                        help="select task out of ['classification','regression'] default: classification")
    parser.add_argument("-e", "--explain", help="explain model", action="store_true")
    parser.add_argument("-mp", "--model_path", type=str, default=None, help="give the model path")
    args = parser.parse_args()
    
    return args

def set_seed(seed):
    # 123 was used originally
    np.random.seed(seed)
    torch.manual_seed(seed)

    
class ClassifierDataset(Dataset):
    def __init__(self, X_data, y_data):
        self.X_data = X_data
        self.y_data = y_data

    def __getitem__(self, index):
        return self.X_data[index], self.y_data[index]

    def __len__(self):
        return len(self.X_data)

def make_one_hot(data, num_categories, dtype=torch.float):
    num_entries = len(data)
    # Convert data to a torch tensor of indices, with extra dimension:
    cats = torch.Tensor(data).long().unsqueeze(1)
    # Now convert this to one-hot representation:
    y = torch.zeros((num_entries, num_categories), dtype=dtype)\
        .scatter(1, cats, 1)
    y.requires_grad = True
    return y

def get_data_one_hot(dataset, n_feature, batch_size, columns_sel):
    import pandas as pd
    dataframe = pd.read_csv('dataset/' + dataset + '/' + dataset + '_train.csv', header=0, sep=',')

    columns_sel.append('Classification')
    
    dataframe = dataframe[columns_sel]

    array = dataframe.values
    d_data = array[:, 0:len(dataframe.columns) - 1]
    d_target = array[:, len(dataframe.columns) - 1]

    X_train, X_val, y_train, y_val = train_test_split(d_data, d_target, test_size=0.2, stratify=d_target, random_state=69, shuffle=True)

    train_dataset = ClassifierDataset(torch.from_numpy(X_train).float(), torch.from_numpy(y_train).long())
    val_dataset = ClassifierDataset(torch.from_numpy(X_val).float(), torch.from_numpy(y_val).long())

    x = torch.Tensor(X_train)
    y = make_one_hot(y_train, num_categories=2)
    td = TensorDataset(x, y)

    return DataLoader(train_dataset, batch_size=batch_size, shuffle=False), DataLoader(val_dataset, batch_size=batch_size), DataLoader(td, batch_size=batch_size, shuffle=False), columns_sel

def train(dataset, n_feature, learning_rate, bs, columns_sel):
    train_data, val_data, x, columns_sel = get_data_one_hot(dataset, n_feature, bs, columns_sel)
    x_train, y_train = x.dataset.tensors
    model = make_anfis(x_train, num_mfs=3, num_out=2, hybrid=False)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    model, score = experimental.train_anfis_cat(model, train_data, val_data, optimizer,100)
    torch.save(model, 'models/model_' + dataset + '.h5')
    load_model.metrics(dataset, columns_sel)
    return model

def train_regression(dataset, n_feature, learning_rate, bs, columns_sel):
    train_data, val_data, x, columns_sel = get_data_one_hot(dataset, n_feature, bs, columns_sel)
    x_train, y_train = x.dataset.tensors
    model = make_anfis(x_train, num_mfs=3, num_out=1, hybrid=False)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    model, score = experimental.train_anfis_cat(model, train_data, val_data, optimizer,100)
    torch.save(model, 'models/model_' + dataset + '.h5')
    load_model.metrics(dataset, columns_sel)
    return model

def opt(dataset, n_feature, learning_rate, bs, file_name, columns_sel):
    train_data, val_data, x, columns_sel = get_data_one_hot(dataset, n_feature, bs, columns_sel)
    x_train, y_train = x.dataset.tensors

    model = make_anfis(x_train, num_mfs=3, num_out=2, hybrid=False)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    model, scores = experimental.train_anfis_cat(model, train_data, val_data, optimizer,100)
    return model, scores

def select_columns(dataset_name):
    if dataset_name == 'sepsis_cases_1':
            columns_sel = ['Diagnose', 'mean_open_cases', 'Age', 'std_Leucocytes', 'std_CRP']#sepsis_cases_1
    elif dataset_name == 'sepsis_cases_2':
            columns_sel = ['Diagnose', 'mean_open_cases', 'mean_hour', 'DisfuncOrg']#sepsis_cases_2
    elif dataset_name == 'sepsis_cases_4':
            columns_sel = ['Diagnose', 'mean_open_cases', 'Age', 'org:group_E', 'std_CRP', 'DiagnosticECG']#sepsis_cases_4
    elif dataset_name == 'bpic2011_f1':
            columns_sel = ['Diagnosis Treatment Combination ID', 'mean_open_cases', 'Diagnosis', 'Activity code_376400.0']#bpic2011_f1
    elif dataset_name == 'bpic2011_f2':
            columns_sel = ['Diagnosis Treatment Combination ID', 'Diagnosis', 'Diagnosis code', 'mean_open_cases', 'Activity code_376400.0', 'Age', 'Producer code_CHE1']#bpic2011_f2
    elif dataset_name == 'bpic2011_f3':
            columns_sel = ['Diagnosis Treatment Combination ID', 'Diagnosis', 'mean_open_cases', 'Diagnosis code', 'std_event_nr', 'mean_event_nr']#bpic2011_f3
    elif dataset_name == 'bpic2011_f4':
            columns_sel = ['Diagnosis Treatment Combination ID', 'Treatment code']#bpic2011_f4
    elif dataset_name == 'bpic2012_accepted':
            columns_sel = ['AMOUNT_REQ', 'Activity_O_SENT_BACK-COMPLETE', 'Activity_W_Valideren aanvraag-SCHEDULE', 'Activity_W_Valideren aanvraag-START']#bpic2012_accepted
    elif dataset_name == 'bpic2012_declined':
            columns_sel = ['AMOUNT_REQ', 'Activity_A_PARTLYSUBMITTED-COMPLETE', 'Activity_A_PREACCEPTED-COMPLETE', 'Activity_A_DECLINED-COMPLETE', 'Activity_W_Completeren aanvraag-SCHEDULE', 'mean_open_cases'] #bpic2012_declined
    elif dataset_name == 'bpic2012_cancelled':
            columns_sel = ['Activity_O_SENT_BACK-COMPLETE', 'Activity_W_Valideren aanvraag-SCHEDULE', 'Activity_W_Valideren aanvraag-START', 'AMOUNT_REQ', 'Activity_W_Valideren aanvraag-COMPLETE', 'Activity_A_CANCELLED-COMPLETE']#bpic2012_cancelled
    elif dataset_name == 'production':
            columns_sel = ['Work_Order_Qty', 'Activity_Turning & Milling - Machine 4', 'Resource_ID0998', 'Resource_ID4794', 'Resource.1_Machine 4 - Turning & Milling'] #production
    
    return dataset_name   
            
def main(args):
    if args.explain:
        model = torch.load(args.model_path)
        print(model.extra_repr())
    else:
        dataset_name = args.dataset_name # 'sepsis_cases_1'
        columns_sel = select_columns(dataset_name)
        params = pkl.load(open('params/'+dataset_name+".p", "rb"))
        print(f"running on dataset: {dataset_name}")
        print("params:")
        print(params)
        n_features = len(columns_sel)
        model = train(
            dataset_name, 
            n_features, 
            params.get('lr'), 
            params.get('batch_size'), 
            columns_sel[:n_features]
        )    

    
if __name__ ==  "__main__":
    args = get_args()
    set_seed(args.seed)
    main(args)