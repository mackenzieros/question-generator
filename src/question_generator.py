import spacy

nlp = spacy.load('en_core_web_sm')

# TODO:
# Generate new type of question where object is found before subject
#   - can include wh-determiner to create new questions
class QuestionGenerator:
    class Question:
        def __init__(self, wh, aux, nsubj, verb, obj):
            '''
            Constructor for the Question class used within the Question Generator
            
            Args:
                wh: string representing WH-
                aux: string representing auxillary verb
                nsubj: string representing subject
                verb: string representing main verb
                obj: string representing object
            '''
            self._wh = wh
            self._aux = aux
            self._nsubj = nsubj if nsubj != 'which' else 'it' # nominal subject refers to 'it'
            self._verb = verb
            self._obj = obj

            if self._verb == self._aux:
                if self._aux == 'has':
                    self._question = ' '.join([self._wh, 'does', self._nsubj, 'have', '?'])
                else:
                    if self._aux == 'to':
                        self._aux = 'will'
                    self._question = ' '.join([self._wh, self._aux.lower(), self._nsubj, '?'])
            else:
                if self._aux == 'has':
                    self._question = ' '.join([self._wh, 'did', self._nsubj, self._verb, '?'])
                else:
                    if self._aux == 'to':
                       self._aux = 'will'
                    self._question = ' '.join([self._wh, self._aux.lower(), self._nsubj, self._verb, '?'])

        
        def __str__(self):
            return self._question


    def __init__(self, doc):
        '''
        Constructor for the Question Generator
        
        Args:
            doc: spacy.Doc
        '''
        self._doc = nlp(doc)
        self._questions = []
        self._generate_questions()
    
    
    def _capitalize_proper_nouns(self, span) -> str:
        '''
        Capitalizes all proper nouns found in the span.
        
        Args:
            span: spacy.Span representing clausal subject
        
        Returns:
            A properly capitalized subject
        '''
        return ' '.join([token.text if token.pos_ == 'PROPN' else token.text.lower() for token in span])


    def _find_nsubj_in_tokens(self, clause) -> 'spacy.Token' or None:
        '''
        Finds a valid nominal subject in the clause.
        
        Args:
            clause: spacy.Span
            
        Returns:
            A spacy.Token of the subject found in the clause or None
        '''
        in_punct = False # ignore all tokens in parentheses, brackets, and curly braces
        for token in clause:
            if token.text in {'(', '[', '{'}:
                in_punct = True
            if token.text in {')', ']', '}'} and in_punct:
                in_punct = False
            if in_punct:
                continue

            # checks for validity of dependency of subject, and whether it's a wh-determiner
            if nlp.vocab[token.dep].text in {'csubj', 'csubjpass', 'nsubj', 'nsubjpass'} and 'wh-determiner' not in spacy.explain(token.tag_):
                return token
        
        return None


    def _determine_wh(self, clause, subj, obj) -> str:
        '''
        Determines the type of WH- for the question.
        
        Args:
            clause: spacy.Span
            obj: spacy.Token
            
        Returns:
            The string representing the WH-
        '''
        # no object in the sentence, ask a why question
        if not obj:
            return 'What'
        
        ent = nlp.vocab[obj.ent_type].text

        if nlp.vocab[subj.dep].text == 'nsubjpass' and subj.text not in {'which', 'that'}:
            return 'How'
        elif ent == 'PERSON':
            return 'Who'
        elif ent == 'GPE':
            return 'Where'
        elif ent == 'DATE':
            return 'When'
        else:
            return 'What'
        
    
    def _fg_aux(self, aux, verb_tense):
        '''
        Fine-grain tunes an auxillary verb according to exceptions found in English.
        
        Args:
            aux: spacy.Token
            
        Returns:
            Changed form of the auxillary verb as a string
        '''
        if aux.text == 'to':
            if verb_tense == 'PRESENT':
                return 'does'
            elif 'PAST' in verb_tense:
                return 'did'
            else:
                return 'will'
        elif aux.text == 'be':
            return 'is'
        else:
            return aux.text

    def _determine_aux(self, clause, verb, verb_tense, subj) -> str:
        '''
        Determines the auxillary verb to be used in the question by checking the verb tense,
        trying to find the aux verb in the sentence, or using defaults.
        
        Args:
            clause: spacy.Span
            verb: spacy.Token
            verb_tense: string
            
        Returns:
            The auxillary verb for the question.
        '''
        # verb is preceded by the auxillary verb
        if verb.nbor(-1).pos_ == 'AUX':
            return self._fg_aux(verb.nbor(-1), verb_tense)
        
        # look for the auxillary verb
        for token in clause:
            if token.pos_ == 'AUX' or nlp.vocab[token.dep].text == 'aux':
                if verb == token: # aux is root verb
                    return self._fg_aux(verb, verb_tense)
                return self._fg_aux(token, verb_tense)
    
        # if no auxillary verb could be found in the sentence, use default aux verb (do)
        if verb_tense == 'PAST_TENSE':
            return 'did'
        elif verb_tense == 'PRESENT':
            if 'non-3rd' in spacy.explain(verb.tag_): # check form of verb
                return 'do'
            return 'does'
        else:
            print('err: could not determine aux verb')
    
    
    def _determine_verb_tense(self, verb) -> str:
        '''
        Determines the tense of a verb.
        
        Args:
            verb: spacy.Token
        
        Returns:
            A string describing the verb's tense
        '''
        verb_detail = spacy.explain(verb.tag_)
        if 'past tense' in verb_detail:
            return 'PAST_TENSE'
        elif 'past principle' in verb_detail:
            return 'PAST_PRIN'
        elif 'past participle' in verb_detail:
            return 'PAST_PART'
        elif 'present' in verb_detail:
            return 'PRESENT'
        elif 'future' in verb_detail:
            return 'FUTURE'
        elif 'base form' in verb_detail:
            return 'BASE'
        else:
            print('err: could not determine verb tense')
    

    def _search_for_object(self, token) -> 'spacy.Token' or None:
        '''
        Performs a depth-first search on the token's subtree in search of the first object.
        
        Args:
            tree: spacy.Token that will act as the root of the tree
            
        Returns:
            Either a token of the object or None
        '''
        if token == None:
            return None
        
        if nlp.vocab[token.dep].text  in {'pobj', 'dobj'}:
            return token
        
        for child in token.children:
            search_res = self._search_for_object(child)
            if search_res:
                return search_res
        

    def _map_syntax(self, start, end) -> dict or None:
        '''
        Function to map the syntax of a clause to its subject, object, and verb.
        Also determines where to split on original spacy.Doc for more efficient parsing.
        
        Args:
            doc: spacy.Doc
            start: int representing the start of clause to analyze
            end: int representing the end of clause to analyze
        
        Returns:
            A dictionary containing the syntax of the clause or None
        '''
        # flags for having found a clause
        subj = None
        obj = None

        clause = self._doc[start:end] # span of clause to analyze
        verb = clause.root
        c_map = dict() # map of sentence syntax
        c_map['end'] = verb.right_edge.i # used to cut iteration

        for chunk in clause.noun_chunks:
            if chunk.root.dep_ in {'csubj', 'csubjpass', 'nsubj', 'nsubjpass'}:
                subj_subtree = [child for child in chunk.subtree]
                
                verb = chunk.root.head # re-assign verb because actual root verb may not be included
                c_map['end'] = verb.right_edge.i

                break
    
        if subj == None:
            # if the subject could not be found iterating through the noun chunks,
            # try iterating through the tokens and look at their dependencies manually
            subj_token = self._find_nsubj_in_tokens(clause)
            if subj_token == None:
                return None
            else:
                subj_subtree = [child for child in subj_token.subtree]

        subj = self._doc[subj_subtree[0].i: subj_subtree[-1].i + 1] # subject is nsubj and all of its children
        # find the object of the sentence
        for child in verb.children:
            obj_found = self._search_for_object(child)
            if obj_found:
                obj = obj_found
                break
        wh = self._determine_wh(clause, subj.root, obj)
        verb_tense = self._determine_verb_tense(verb)
        aux = self._determine_aux(clause, verb, verb_tense, subj)
        
        if verb_tense in {'PAST_TENSE', 'PRESENT'} and verb.text != aux:
            verb_text = verb.lemma_
        else:
            verb_text = verb.text
        
        c_map['wh'] = wh
        c_map['nsubj'] = subj
        c_map['obj'] = obj
        c_map['verb'] = verb_text
        c_map['aux'] = aux

        return c_map


    def _generate_questions(self) -> None:
        '''
        Generates questions from a spacy.Doc object. 
        Breaks up the doc into clauses, parses each clause for its syntax and creates a question from it.
        '''
        start = 0
        end = start + 1
        
        in_punct = False # flag to ignore all words contained in parantheses, brackets, and curly braces
        while end < len(self._doc) and start < end:
            token = self._doc[end]
            
            if token.text in {'(', '[', '{'}:
                in_punct = True
            if token.text in {')', ']', '}'} and in_punct:
                in_punct = False
            if in_punct:
                end += 1
                continue
                
            # only generate a question when we encounter a sentence closer, coord-conjunction, or end of sentence
            if token.text not in {'.', '!' ,'?' , ';', '--', '...'} and nlp.vocab[token.dep].text not in {'cc'}:
                end += 1
                continue

            # parse the clause for syntax (nominal subject, verb, etc.)
            c_map = self._map_syntax(start, end)

            if c_map == None or None in {c_map['wh'], c_map['aux'], c_map['nsubj'], c_map['verb']}:
                end += 1
                continue
            
            start = c_map['end']
            end = start

            self._questions.append(QuestionGenerator.Question(
                c_map['wh'], 
                c_map['aux'], 
                self._capitalize_proper_nouns(c_map['nsubj']),
                c_map['verb'].lower(),
                c_map['obj'],
            ))
            end += 1

        # attempt to make a question from remainder of sentence
        if start < len(self._doc):
            c_map = self._map_syntax(start, len(self._doc))
            if c_map == None:
                return

            if None in {c_map['wh'], c_map['aux'], c_map['nsubj'], c_map['verb']}:
                return
            
            self._questions.append(QuestionGenerator.Question(
                c_map['wh'], 
                c_map['aux'], 
                self._capitalize_proper_nouns(c_map['nsubj']), 
                c_map['verb'].lower(),
                c_map['obj'],
            ))

    def get_questions(self) -> list:
        '''
        Returns all of the questions contained in the Question Generator
        '''
        return self._questions


if __name__ == '__main__':
    doc_str = u'A* (pronounced "A-star") is a graph traversal and path search algorithm, and it is often used in computer science due to its completeness,'
    u' optimality, and optimal efficiency. One major practical drawback is its O(b^d) space complexity, as it stores all generated nodes in memory.'
    qg = QuestionGenerator(doc_str)
    questions = qg.get_questions()
    for q in questions:
      print(q)