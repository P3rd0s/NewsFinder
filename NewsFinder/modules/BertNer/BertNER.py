import os.path

import requests
import torch
from torch import cuda
from transformers import BertTokenizerFast, BertForTokenClassification

from NewsFinder.constants.mapping import id_to_label

MAX_LEN = 128
TRAIN_BATCH_SIZE = 4
VALID_BATCH_SIZE = 2
EPOCHS = 3
LEARNING_RATE = 1e-05
MAX_GRAD_NORM = 10

MODEL_PATH = 'modules/BertNer/model'
MODEL_CONFIG = MODEL_PATH + '/config.json'
MODEL_BIN = MODEL_PATH + '/pytorch_model.bin'
MODEL_VOCAB = MODEL_PATH + '/vocab.txt'


class BertNer:
    device_name = 'cpu'
    tokenizer = None
    model = None

    def __init__(self):
        if cuda.is_available():
            self.device_name = 'cuda'
            print('Используется графический процессор с ядрами Cuda')
        else:
            self.device_name = 'cpu'
            print('Используется центральный процессор')

        if os.path.isdir(MODEL_PATH):
            self.init_model()
        else:
            config_url = os.environ.get('MODEL_CONFIG_URL', 'https://www.dropbox.com/s/y9ajnw755uz3pb2/config.json?dl=1')
            model_url = os.environ.get('MODEL_URL', 'https://www.dropbox.com/s/9jlc9rwzckptva9/pytorch_model.bin?dl=1')
            vocab_url = os.environ.get('MODEL_VOCAB_URL', 'https://www.dropbox.com/s/pzgexbgd5tdzopy/vocab.txt?dl=1')

            os.mkdir(MODEL_PATH)
            r = requests.get(config_url, stream=True)
            with open(MODEL_CONFIG, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                f.close()

            r = requests.get(model_url, stream=True)
            with open(MODEL_BIN, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                f.close()

            r = requests.get(vocab_url, stream=True)
            with open(MODEL_VOCAB, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                f.close()

            self.init_model()

    def init_model(self):
        self.tokenizer = BertTokenizerFast.from_pretrained(MODEL_PATH)
        self.model = BertForTokenClassification.from_pretrained(MODEL_PATH)
        self.model = self.model.to(self.device_name)
        self.model.eval()

    def is_ioc(self, sentence):
        inputs = self.tokenizer(sentence, padding='max_length', truncation=True, max_length=MAX_LEN, return_tensors="pt")

        # Вычисление на графическом процессоре
        ids = inputs["input_ids"].to(self.device_name)
        mask = inputs["attention_mask"].to(self.device_name)
        # forward pass
        outputs = self.model(ids, mask)
        logits = outputs[0]

        active_logits = logits.view(-1, self.model.num_labels)  # shape (batch_size * seq_len, num_labels)
        flattened_predictions = torch.argmax(active_logits, axis=1)  # shape (batch_size*seq_len,) - Предсказания на уровне токенов

        tokens = self.tokenizer.convert_ids_to_tokens(ids.squeeze().tolist())
        token_predictions = [id_to_label[i] for i in flattened_predictions.cpu().numpy()]
        wp_preds = list(zip(tokens, token_predictions))  # Список кортежей. Каждый кортеж = (подслово, предсказание)

        word_level_predictions = []
        for pair in wp_preds:
            if (pair[0].startswith(" ##")) or (pair[0] in ['[CLS]', '[SEP]', '[PAD]']):
                # Не предсказывать подслова и специальные токены
                continue
            else:
                word_level_predictions.append(pair[1])

        # Восстановление предложения без специальных токенов
        # str_rep = " ".join([t[0] for t in wp_preds if t[0] not in ['[CLS]', '[SEP]', '[PAD]']]).replace(" ##", "")
        # print(str_rep)
        # print(word_level_predictions)

        return id_to_label[4] in word_level_predictions or\
               id_to_label[5] in word_level_predictions or\
               id_to_label[6] in word_level_predictions or\
               id_to_label[7] in word_level_predictions or\
               id_to_label[9] in word_level_predictions or\
               id_to_label[10] in word_level_predictions
