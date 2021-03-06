#!/usr/bin/env python2

'''
adapted from https://github.com/HamedMP/ImageFlow/blob/master/example_project/input_data.py
and https://github.com/tensorflow/tensorflow/blob/master/tensorflow/examples/how_tos/reading_data/fully_connected_reader.py
'''
import tensorflow as tf
import imageflow
import numpy
import glob
import sys
import os

DATA_DIRECTORY = '/home/drivers/CarHawk/data' 

def _int64_feature(value):
  return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))

def _bytes_feature(value):
  return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))

def read_images(path):
	print 'reading images from', path
	images     = []
	reader     = tf.WholeFileReader()
	png_files  = glob.glob(os.path.join(path, '*.png'))
	total_pngs = len(png_files)
	png_file_q = tf.train.string_input_producer(png_files)
	pkey, pval = reader.read(png_file_q)
	p_image    = tf.image.decode_png(pval)
	
	with tf.Session() as sess:
		coord   = tf.train.Coordinator()
		threads	= tf.train.start_queue_runners(coord=coord)
		for i in range(total_pngs):
			sys.stdout.write('\r>> Loaded %s %.1f%%' % (png_files[i],
				float(i) / float(total_pngs) * 100.0))
			sys.stdout.flush()
			png = p_image.eval()
			images.append(png)
		print 
		coord.request_stop()
		coord.join(threads)
	return images

def convert_to(images, labels, name):
	num_examples = labels.shape[0]
	if images.shape[0] != num_examples:
		raise ValueError("Images size %d does not match label size %d." %
				 (images.shape[0], num_examples))
	rows = images.shape[1]
	cols = images.shape[2]
	depth = images.shape[3]

	filename = os.path.join(DATA_DIRECTORY, name + '.tfrecords')
	print 'Writing', filename
	writer = tf.python_io.TFRecordWriter(filename)
	for index in range(num_examples):
		image_raw = images[index].tostring()
		example = tf.train.Example(features=tf.train.Features(feature={
			'height': _int64_feature(rows),
			'width':  _int64_feature(cols),
			'depth':  _int64_feature(depth),
			'label':  _int64_feature(int(labels[index])),
			'image_raw': _bytes_feature(image_raw)}))
		writer.write(example.SerializeToString())
	writer.close()

def read_and_decode(filename_queue):
	reader = tf.TFRecordReader()
	_, serialized_example = reader.read(filename_queue)
	features = tf.parse_single_example(
		serialized_example,
		# Defaults are not specified since both keys are required.
		features={
			'image_raw': tf.FixedLenFeature([], tf.string),
			'label':     tf.FixedLenFeature([], tf.int64),
		})
	
	# Convert from a scalar string tensor (whose single string has
	# length mnist.IMAGE_PIXELS) to a uint8 tensor with shape
	# [mnist.IMAGE_PIXELS].
	image = tf.decode_raw(features['image_raw'], tf.uint8)
	image.set_shape([160, 120, 3])

	# OPTIONAL: Could reshape into a 28x28 image and apply distortions
	# here.  Since we are not applying any distortions in this
	# example, and the next step expects the image to be flattened
	# into a vector, we don't bother.

	# Convert from [0, 255] -> [-0.5, 0.5] floats.
	image = tf.cast(image, tf.float32) * (1. / 255) - 0.5

	# Convert label from a scalar uint8 tensor to an int32 scalar.
	label = tf.cast(features['label'], tf.int32)

	return image, label

def inputs(filepath, batch_size, num_epochs):
	with tf.name_scope('input'):
		filename_queue = tf.train.string_input_producer(
			[filepath], num_epochs=num_epochs)

		# Even when reading in multiple threads, share the filename
		# queue.
		image, label = read_and_decode(filename_queue)

		# Shuffle the examples and collect them into batch_size batches.
		# (Internally uses a RandomShuffleQueue.)
		# We run this in two threads to avoid being a bottleneck.
		images, sparse_labels = tf.train.shuffle_batch(
			[image, label], batch_size=batch_size, num_threads=2,
			capacity=1000 + 3 * batch_size,
			# Ensures a minimum amount of shuffling of examples.
			min_after_dequeue=1000)	

		return images, sparse_labels

def read_image(path):
	print 'reading image from', path
	image      = []
	reader     = tf.WholeFileReader()
	png_files  = [path]
	total_pngs = len(png_files)
	png_file_q = tf.train.string_input_producer(png_files)
	pkey, pval = reader.read(png_file_q)
	p_image    = tf.image.decode_png(pval)
	
	with tf.Session() as sess:
		coord   = tf.train.Coordinator()
		threads	= tf.train.start_queue_runners(coord=coord)
		for i in range(total_pngs):
			png = p_image.eval()
			image.append(png)
		print 
		coord.request_stop()
		coord.join(threads)
	return image[0]

def convert_without_label_to(image, name):
	rows = image.shape[0]
	cols = image.shape[1]
	depth = image.shape[2]
	filename = os.path.join(DATA_DIRECTORY, 'validate/', name + '.tfrecords')
	print 'Writing', filename
	writer = tf.python_io.TFRecordWriter(filename)
	image_raw = image.tostring()
	example = tf.train.Example(features=tf.train.Features(feature={
		'height': _int64_feature(rows),
		'width':  _int64_feature(cols),
		'depth':  _int64_feature(depth),
		'image_raw': _bytes_feature(image_raw)}))
	writer.write(example.SerializeToString())
	writer.close()

def main():
	
	test_images   = glob.glob('/home/drivers/CarHawk/images/test_all/*')
	tfrecord_ids  = [path.split('/')[-1].split('.')[0] for path in glob.glob('/home/drivers/CarHawk/data/validation/*')]
	total_imgs    = len(test_images)
	step          = 0.0
	for path in test_images:	
		if path.split('/')[-1].split('.')[0] not in tfrecord_ids:
			print 'converting', path
			image = read_image(path)
			convert_without_label_to(image, path.split('/')[-1].split('.')[0])
		print step / total_imgs * 100.0
		step += 1

	'''
	validation = read_images('/home/jared/CarHawk/images/test_all/')
	train_c0   = read_images('/home/jared/CarHawk/images/train_all/c0')
	train_c1   = read_images('/home/jared/CarHawk/images/train_all/c1')
	train_c2   = read_images('/home/jared/CarHawk/images/train_all/c2')
	train_c3   = read_images('/home/jared/CarHawk/images/train_all/c3')
	train_c4   = read_images('/home/jared/CarHawk/images/train_all/c4')
	train_c5   = read_images('/home/jared/CarHawk/images/train_all/c5')
	train_c6   = read_images('/home/jared/CarHawk/images/train_all/c6')
	train_c7   = read_images('/home/jared/CarHawk/images/train_all/c7')
	train_c8   = read_images('/home/jared/CarHawk/images/train_all/c8')
	train_c9   = read_images('/home/jared/CarHawk/images/train_all/c9')
	
	convert_to(numpy.array(validation), numpy.array([-1 for i in range(len(validation))]), 'validation')
	convert_to(numpy.array(train_c0),   numpy.array([0 for i in range(len(train_c0))]), 'train_c0')
	convert_to(numpy.array(train_c1),   numpy.array([1 for i in range(len(train_c1))]), 'train_c1')
	convert_to(numpy.array(train_c2),   numpy.array([2 for i in range(len(train_c2))]), 'train_c2')
	convert_to(numpy.array(train_c3),   numpy.array([3 for i in range(len(train_c3))]), 'train_c3')
	convert_to(numpy.array(train_c4),   numpy.array([4 for i in range(len(train_c4))]), 'train_c4')
	convert_to(numpy.array(train_c5),   numpy.array([5 for i in range(len(train_c5))]), 'train_c5')
	convert_to(numpy.array(train_c6),   numpy.array([6 for i in range(len(train_c6))]), 'train_c6')
	convert_to(numpy.array(train_c7),   numpy.array([7 for i in range(len(train_c7))]), 'train_c7')
	convert_to(numpy.array(train_c8),   numpy.array([8 for i in range(len(train_c8))]), 'train_c8')
	convert_to(numpy.array(train_c9),   numpy.array([9 for i in range(len(train_c9))]), 'train_c9')
	
	print inputs(os.path.join(DATA_DIRECTORY, 'validation.tfrecords'), 128, 2) 
	print inputs(os.path.join(DATA_DIRECTORY, 'train_c0.tfrecords'), 128, 2) 
	print inputs(os.path.join(DATA_DIRECTORY, 'train_c1.tfrecords'), 128, 2) 
	print inputs(os.path.join(DATA_DIRECTORY, 'train_c2.tfrecords'), 128, 2) 
	print inputs(os.path.join(DATA_DIRECTORY, 'train_c3.tfrecords'), 128, 2) 
	print inputs(os.path.join(DATA_DIRECTORY, 'train_c4.tfrecords'), 128, 2) 
	print inputs(os.path.join(DATA_DIRECTORY, 'train_c5.tfrecords'), 128, 2) 
	print inputs(os.path.join(DATA_DIRECTORY, 'train_c6.tfrecords'), 128, 2) 
	print inputs(os.path.join(DATA_DIRECTORY, 'train_c7.tfrecords'), 128, 2) 
	print inputs(os.path.join(DATA_DIRECTORY, 'train_c8.tfrecords'), 128, 2) 
	print inputs(os.path.join(DATA_DIRECTORY, 'train_c9.tfrecords'), 128, 2) 
	'''
if __name__=='__main__': main()
