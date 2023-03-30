from django.core.paginator import Paginator

from posts import constants


def paginate(request, post_list):
    paginator = Paginator(post_list, constants.POST_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
