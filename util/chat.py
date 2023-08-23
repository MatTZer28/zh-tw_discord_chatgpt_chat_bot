import os

import openai
import gensim

from util.logger import logger

from opencc import OpenCC

OPENAI_KEY = os.getenv('OPENAI_KEY') # Put yor OpenAI API key here
MODEL = 'gpt-3.5-turbo'
TEMPERATURE = 0.75
PRESENCE_PENALTY = 0
FREQUENCY_PENALTY = 0
ABSTRACTION_WINDOW = 3  # Must be odd numbers
SIM_THRES = 0.7 # Similarity Threshold
TOPN = 20 # Take top N most similar sentences
INIT_PROMT_PATH = 'prompt/xxx.txt' # Make your own initial system prompt
ABSTRACT_PROMT_PATH = 'prompt/abstract.txt' # Empowering AI to summarize prompts
KEYEDVECTORS_SAVE_PATH = 'keyedvectors/keyed_vectors.kv'

openai.api_key = OPENAI_KEY
# openai.api_base = "https://chimeragpt.adventblocks.cc/api/v1"

cc = OpenCC('s2twp')

with open(INIT_PROMT_PATH, 'r') as f:
  INIT_PROMT = f.read()
  logger.info(f'INIT_PROMT: \'{INIT_PROMT_PATH}\' Loaded')

with open(ABSTRACT_PROMT_PATH, 'r') as f:
  ABSTRACT_PROMT = f.read()
  logger.info(f'ABSTRACT_PROMT_PATH: \'{ABSTRACT_PROMT_PATH}\' Loaded')


class Chat(openai.ChatCompletion):

  msg_keys = ['role', 'content']
  msg_format = {'role': None, 'content': None}
  msg_roles = ['system', 'user', 'assistant']

  def __init__(self,
               model=MODEL,
               temperature=TEMPERATURE,
               presence_penalty=PRESENCE_PENALTY,
               frequency_penalty=FREQUENCY_PENALTY):
    self._model = model
    self._temperature = temperature
    self._presence_penalty = presence_penalty
    self._frequency_penalty = frequency_penalty
    self._messages = []
    self._msg_count = 0
    self._runtime_kv = []
    self._curr_similar_count = 0

  def _send(self, messages):
    try:
      return self.create(model=self._model,
                         messages=messages,
                         temperature=self._temperature,
                         presence_penalty=self._presence_penalty,
                         frequency_penalty=self._frequency_penalty)
    except Exception as e:
      logger.error(e)
      raise

  def _create_msg(self, role, content):
    msg = Chat.msg_format.copy()

    msg[Chat.msg_keys[0]] = role
    msg[Chat.msg_keys[1]] = content

    return msg

  def init(self):
    try:
      init_msg = self._create_msg(Chat.msg_roles[0], INIT_PROMT)
      self._messages.append(init_msg)
      logger.info('INIT_PROMT')

      respond = cc.convert(self._send(self._messages)['choices'][0]['message']['content'])
      
      res_msg = self._create_msg(Chat.msg_roles[2], respond)
      self._messages.append(res_msg)
      self._msg_count += 1
      logger.info(res_msg)

      return respond

    except:
      raise

  def _del_similar_msgs(self):
    del self._messages[1:(1+self._curr_similar_count)]

  async def do_abstract(self):
    if self._msg_count != ABSTRACTION_WINDOW:
      return
      
    self._msg_count = 0

    context = ABSTRACT_PROMT + '\"'

    for msg in self._messages:
      role = msg[Chat.msg_keys[0]]

      if role == Chat.msg_roles[0]:
        continue

      content = msg[Chat.msg_keys[1]]

      context = context + f'{role}:{content}' + '\n'

    context = context + '\"'

    messages = [self._create_msg(Chat.msg_roles[0], context)]
    respond = cc.convert(self._send(messages)['choices'][0]['message']['content'])
    
    res_msg = self._create_msg(Chat.msg_roles[2], respond)

    self._messages = [self._messages[0]]
    self._messages.append(res_msg)
    self._msg_count += 1
    logger.info(res_msg)

  def _add_similar_msgs(self):
    saved_kv = None
    
    if os.path.exists(KEYEDVECTORS_SAVE_PATH):
      saved_kv = gensim.models.keyedvectors.KeyedVectors.load(KEYEDVECTORS_SAVE_PATH)
    else:
      saved_kv = gensim.models.keyedvectors.KeyedVectors(100)
      
    for i in range(len(self._runtime_kv) - self._msg_count):
      saved_kv.add_vector(self._runtime_kv[i][0], self._runtime_kv[i][1])
      
    saved_kv.add_vector(self._runtime_kv[-1][0], self._runtime_kv[-1][1])
    
    saved_kv.save(KEYEDVECTORS_SAVE_PATH)

    context = self._runtime_kv[-1][0]
    similars = saved_kv.most_similar(positive=[context], topn=TOPN)
    self._curr_similar_count = len(similars)

    for key, similarity in similars:
      if similarity < SIM_THRES:
        continue
      
      role, *content = key.split(':')

      msg = None
      if len(content) > 1:
        content = " ".join(content)
        msg = self._create_msg(role, content)
      else:
        msg = self._create_msg(role, content[0])
        
      self._messages.insert(1, msg)

  def _to_vector(self, context):
    model = gensim.models.Word2Vec(window=5, min_count=1, workers=4, sg=0)
    model.build_vocab([context])
    model.train([context],
                total_examples=model.corpus_count,
                epochs=model.epochs)
    mean_vector = model.wv.get_mean_vector(model.wv.key_to_index.keys(), post_normalize=True)
    return mean_vector

  def _get_context(self, msg):
    role = msg[Chat.msg_keys[0]]
    content = msg[Chat.msg_keys[1]]
    return f'{role}:{content}'

  def _save_vector(self, msg):
    context = self._get_context(msg)
    mean_vector = self._to_vector(context)
    self._runtime_kv.append([context, mean_vector])

  def talk(self, content):
    try:
      send_msg = self._create_msg(Chat.msg_roles[1], content)
      self._messages.append(send_msg)
      self._msg_count += 1
      logger.info(send_msg)
      self._save_vector(send_msg)
      self._add_similar_msgs()

      respond = cc.convert(self._send(self._messages)['choices'][0]['message']['content'])
      
      res_msg = self._create_msg(Chat.msg_roles[2], respond)
      self._messages.append(res_msg)
      self._msg_count += 1
      logger.info(res_msg)
      self._save_vector(res_msg)

      return respond
    except:
      self._messages = self._messages[:-1]
      self._runtime_kv = self._runtime_kv[:-1]
      self._msg_count -= 1
      raise

    finally:
      self._del_similar_msgs()