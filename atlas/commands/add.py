import logging
import os
import csv
import vcf
from mongoengine import connect
from mongoengine import NotUniqueError
from mongoengine import OperationError
from pymongo import MongoClient
from atlas.variants.models import CallSet
from atlas.variants.models import Reference
from atlas.variants.models import Variant
from atlas.variants.models import VariantSet
from atlas.variants.models import Call
from atlas.utils import check_args
"""Adds variants to the database"""

LOGGER = logging.getLogger("logger")
client = MongoClient()


def is_record_valid(record):
    valid = True
    for sample in record.samples:
        if sample["GT"] is None:
            valid = False
        else:
            if sum([int(i) for i in sample['GT'].split('/')]) < 2:
                valid = False
        try:
            if sample["GT_CONF"] <= 1:
                valid = False
        except AttributeError:
            pass
    return valid


def get_genotype_likelihood(sample):
    try:
        genotype_likelihood = sample['GT_CONF']
    except AttributeError:
        genotype_likelihood = sample['GQ']
    return genotype_likelihood


def run(parser, args):
    args = parser.parse_args()
    args = check_args(args)
    if args.quiet:
        LOGGER.setLevel(logging.ERROR)
    else:
        LOGGER.setLevel(logging.INFO)
    DBNAME = 'atlas-%s-%i' % (args.db_name, args.kmer)
    db = client[DBNAME]
    connect(DBNAME)
    LOGGER.debug("Using DB %s" % DBNAME)

    vcf_reader = vcf.Reader(open(args.vcf, 'r'))
    assert len(vcf_reader.samples) == 1

    variant_set_name = os.path.splitext(os.path.basename(args.vcf))[0]
    if args.sample is None:
        sample = vcf_reader.samples[0]
    else:
        sample = args.sample

    try:
        callset = CallSet.create(name=variant_set_name, sample_id=sample)
    except NotUniqueError:
        callset = CallSet.objects.get(name=variant_set_name)

    try:
        variant_set = VariantSet.create(name=variant_set_name)
    except NotUniqueError:
        variant_set = VariantSet.objects.get(name=variant_set_name)

    try:
        reference = Reference.create(name="R00000022")
    except NotUniqueError:
        reference = Reference.objects.get(name="R00000022")

    variants = []
    calls = []
    for record in vcf_reader:
        if not record.FILTER and is_record_valid(record) and record.is_snp:
            for sample in record.samples:
                try:
                    v = Variant.create_object(
                        variant_set=variant_set,
                        start=record.POS,
                        reference_bases=record.REF,
                        alternate_bases=[
                            str(a) for a in record.ALT],
                        reference=reference)
                except (OperationError, ValueError) as e:
                    print e
                    print record.POS
                    print record
                else:
                    variants.append(v)
                    genotype_likelihood = get_genotype_likelihood(sample)
                    c = Call.create_object(
                        variant=v,
                        call_set=callset,
                        genotype=sample['GT'],
                        genotype_likelihood=genotype_likelihood)
                    calls.append(c)
    try:
        variant_ids = [v.id for v in Variant.objects.insert(variants)]
    except (NotUniqueError) as e:
        LOGGER.error(str(e))
        LOGGER.error("Variants must be unique within a given VCF")
    else:
        LOGGER.info("Uploaded %i variants to database" % len(variant_ids))
        for i, _id in enumerate(variant_ids):
            calls[i]["variant"] = _id
        db.call.insert(calls)
