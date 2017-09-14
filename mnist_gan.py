
import tensorflow as tf
import numpy as np
import pickle
import matplotlib.pyplot as plt

from tensorflow.examples.tutorials.mnist import input_data
mnist = input_data.read_data_sets('./MNIST_data/')


real_img_size = mnist.train.images[0].shape[0]

noise_img_size = 100

g_uints = 128

d_uints = 128

alpha = 0.01

learning_rate = 1e-3

smooth = 0.1

# train
batch_size = 50
batch_num = mnist.train.num_examples//batch_size

epochs = 100


def get_inputs(real_img_size, noise_img_size):
	"""
	read image tensor and noise image tensor
	"""
	real_img = tf.placeholder(tf.float32, shape=(None, real_img_size), name="real_img")
	noise_img = tf.placeholder(tf.float32, shape=(None, noise_img_size), name="noise_img")
	return real_img, noise_img


def get_generator(noise_img, n_units, out_dim, reuse=False, alpha=0.01):
	"""
	generator

	noise_img: input of generator
	n_units: # hidden units
	out_dim: # output
	alpha: parameter of leaky ReLU 
	"""
	with tf.variable_scope("generator", reuse=reuse):
		# hidden layer
		hidden = tf.layers.dense(noise_img, n_units)
		# leaky Relu
		relu = tf.maximum(alpha * hidden, hidden)
		# dropout
		drop = tf.layers.dropout(hidden, rate=0.5)

		# logits & output
		logits = tf.layers.dense(drop, out_dim)
		outputs = tf.tanh(logits)

		return logits, outputs


def get_discriminator(img, n_units, reuse=False, alpha=0.01):
	"""
	discriminator

	n_units: # hidden units
	alpha: parameter of leaky Relu
	"""
	with tf.variable_scope("discriminator", reuse=reuse):
		# hidden layer
		hidden = tf.layers.dense(img, n_units)
		relu = tf.maximum(alpha * hidden, hidden)

		# logits & outputs
		logits = tf.layers.dense(relu, 1)
		outputs = tf.sigmoid(logits)

		return logits, outputs


with tf.Graph().as_default():

	real_img, noise_img = get_inputs(real_img_size, noise_img_size)

	# generator
	g_logits, g_outputs = get_generator(noise_img, g_uints, real_img_size)

	#ten = tf.convert_to_tensor(g_outputs)
	#sample_images = tf.reshape(g_outputs, [-1, 28, 28, 1])
	#tf.summary.image("sample_images", sample_images, 10)


	# discriminator
	d_logits_real, d_outputs_real = get_discriminator(real_img, d_uints)
	d_logits_fake, d_outputs_fake = get_discriminator(g_outputs, d_uints, reuse=True)


	# d loss
	d_loss_real = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(
		logits = d_logits_real,
		labels = tf.ones_like(d_logits_real)) * (1 - smooth))

	d_loss_fake = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(
		logits = d_logits_fake,
		labels = tf.zeros_like(d_logits_fake)))

	d_loss = tf.add(d_loss_real, d_loss_fake)

	# g loss
	g_loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(
		logits = d_logits_fake,
		labels = tf.ones_like(d_logits_fake)) * (1 - smooth))


	tf.summary.scalar("d_loss_real", d_loss_real)
	tf.summary.scalar("d_loss_fake", d_loss_fake)
	tf.summary.scalar("d_loss", d_loss)
	tf.summary.scalar("g_loss", g_loss)

	# optimizer
	train_vars = tf.trainable_variables()

	g_vars = [var for var in train_vars if var.name.startswith("generator")]

	d_vars = [var for var in train_vars if var.name.startswith("discriminator")]

	d_train_opt = tf.train.AdamOptimizer(learning_rate).minimize(d_loss, var_list = d_vars)

	g_train_opt = tf.train.AdamOptimizer(learning_rate).minimize(g_loss, var_list = g_vars)

	summary = tf.summary.merge_all()

	init = tf.global_variables_initializer()
	# save generator variables
	saver = tf.train.Saver()

	sess = tf.Session()

	summary_writer = tf.summary.FileWriter("./log", sess.graph)

	# Run the Op to initialize the variables.
	sess.run(init)

	for e in xrange(epochs):
		for batch_i in xrange(batch_num):
			batch = mnist.train.next_batch(batch_size)

			images = batch[0].reshape((batch_size, 784))
			# scale the input images
			images = 2 * images - 1

			# generator input noises
			noises = np.random.uniform(-1, 1, size=(batch_size, noise_img_size))

			# Run optimizer
			sess.run([d_train_opt, g_train_opt], feed_dict = {real_img: images, noise_img: noises})

		# train loss
		images_test = 2 * mnist.test.images - 1
		noises_test = np.random.uniform(-1, 1, size=(mnist.test.num_examples, noise_img_size))

		summary_str, train_loss_d_real, train_loss_d_fake, train_loss_g = sess.run([summary, d_loss_real, d_loss_fake, g_loss], feed_dict = {real_img: images_test, noise_img: noises_test})

		summary_writer.add_summary(summary_str, e)
		summary_writer.flush()

		
		train_loss_d = train_loss_d_real + train_loss_d_fake
		

		print("Epoch {}/{}".format(e+1, epochs),
			"Discriminator loss: {}(Real: {} + Fake: {})".format(train_loss_d, train_loss_d_real, train_loss_d_fake),
			"Generator loss: {}".format(train_loss_g))

		# losses.append((train_loss_d, train_loss_d_real, train_loss_d_fake, train_loss_g))

		# sample_noise = np.random.uniform(-1, 1, size=(n_samples, noise_img_size))
		# gen_samples = sess.run(get_generator(noise_img, g_uints, real_img_size, reuse = True),
		#	feed_dict = {noise_img: sample_noise})

		# samples.append(gen_samples)

		# save checkpoints
		saver.save(sess, './log/model.ckpt', global_step=e)

