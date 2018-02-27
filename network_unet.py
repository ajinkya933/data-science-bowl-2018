import tensorflow as tf
from tensorflow.contrib import slim
from network_basic import NetworkBasic


class NetworkUnet(NetworkBasic):
    def __init__(self, batchsize):
        super(NetworkUnet, self).__init__(batchsize=batchsize)

    @staticmethod
    def double_conv(net, nb_filter, scope):
        net = slim.convolution(net, nb_filter, [3, 3], 1, scope='%s_1' % scope)
        net = slim.convolution(net, nb_filter, [3, 3], 1, scope='%s_2' % scope)
        return net

    def build(self):
        # https://github.com/tensorflow/tensorflow/blob/master/tensorflow/contrib/layers/python/layers/layers.py#L429
        batch_norm_params = {
            'is_training': self.is_training,
            'center': True,
            'scale': False,
            'decay': 0.9,
            'epsilon': 0.001,
            'fused': True,
            'zero_debias_moving_mean': True
        }

        conv_args = {
            'padding': 'SAME',
            'weights_initializer': tf.truncated_normal_initializer(mean=0.0, stddev=0.001),
            'normalizer_fn': slim.batch_norm,
            'normalizer_params': batch_norm_params,
            'activation_fn': tf.nn.relu6
        }

        net = self.input_batch
        features = []

        with slim.arg_scope([slim.convolution, slim.conv2d_transpose], **conv_args):
            # down sampling steps
            for i in range(4):
                net = NetworkUnet.double_conv(net, int(32*(2**i)), scope='down_conv_%d' % (i + 1))
                features.append(net)
                net = slim.max_pool2d(net, [3, 3], 2, padding='SAME', scope='pool%d' % (i + 1))
            # middle
            net = NetworkUnet.double_conv(net, 512, scope='middle_conv_1')
            # upsampling steps
            for i in range(4):
                net = slim.conv2d_transpose(net, int(256/(2**i)), [3, 3], 2, scope='up_trans_conv_%d' % (i + 1))
                down_feat = features.pop() # upsample with origin version
                net = tf.concat([down_feat, net], axis=-1)
                net = NetworkUnet.double_conv(net, int(256/(2**i)), scope='up_conv_%d' % (i + 1))

            net = NetworkUnet.double_conv(net, 32, scope='output_conv_1')
        net = slim.convolution(net, 1, [3, 3], 1, scope='final_conv',
                               padding='SAME', weights_initializer= tf.truncated_normal_initializer(mean=0.0, stddev=0.01))

        self.logit = net
        self.output = tf.nn.sigmoid(net, 'visualization')
        self.loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(labels=self.mask_batch, logits=self.logit))
        return net
