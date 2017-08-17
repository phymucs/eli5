from itertools import repeat
from collections import Counter

import pytest
import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

from eli5.sklearn.unhashing import InvertableHashingVectorizer
from eli5.sklearn.utils import sklearn_version

@pytest.mark.parametrize(
    ['always_signed', 'binary', 'non_negative'], [
        [True, False, False],
        [False, False, False],
        [False, True, False],
        [True, True, False],
    ] + [] if (sklearn_version() >= '0.19') else [
        [False, True, True],
        [False, False, True],
        [True, False, True],
    ],
)
def test_invertable_hashing_vectorizer(always_signed, binary, non_negative):
    n_features = 8
    n_words = 4 * n_features
    kwargs = dict(n_features=n_features, binary=binary)
    if non_negative:
        kwargs['non_negative'] = non_negative
    vec = HashingVectorizer(**kwargs)
    words = ['word_{}'.format(i) for i in range(n_words)]
    corpus = [w for i, word in enumerate(words, 1) for w in repeat(word, i)]
    split = len(corpus) // 2
    doc1, doc2 = ' '.join(corpus[:split]), ' '.join(corpus[split:])

    ivec = InvertableHashingVectorizer(vec)
    ivec.fit([doc1, doc2])
    check_feature_names(vec, ivec, always_signed, corpus)

    ivec = InvertableHashingVectorizer(vec)
    ivec.partial_fit([doc1])
    ivec.partial_fit([doc2])
    check_feature_names(vec, ivec, always_signed, corpus)

    ivec = InvertableHashingVectorizer(vec)
    for w in corpus:
        ivec.partial_fit([w])
    check_feature_names(vec, ivec, always_signed, corpus)


def check_feature_names(vec, ivec, always_signed, corpus):
    feature_names = ivec.get_feature_names(always_signed=always_signed)
    seen_words = set()
    counts = Counter(corpus)
    for idx, collisions in enumerate(feature_names):
        words_in_collision = []
        for ic, collision in enumerate(collisions):
            sign = collision['sign']
            c = collision['name']
            if ic == 0 and not always_signed:
                # Most frequent term is always not inverted.
                assert sign == 1, collisions
            seen_words.add(c)
            words_in_collision.append(c)
            if not always_signed and ivec.column_signs_[idx] < 0:
                sign *= -1
            # Term hashes to correct value with correct sign.
            expected = np.zeros(vec.n_features)
            expected[idx] = sign
            transormed = vec.transform([c]).toarray()
            assert np.allclose(transormed, expected), (transormed, expected)
        for prev_w, w in zip(words_in_collision, words_in_collision[1:]):
            # Terms are ordered by frequency.
            assert counts[prev_w] > counts[w]
    assert seen_words == set(corpus)
