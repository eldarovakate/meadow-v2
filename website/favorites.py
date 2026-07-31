SESSION_KEY = "favorite_product_ids"


def get_favorite_ids(request):
    return set(request.session.get(SESSION_KEY, []))


def toggle_favorite(request, page_id):
    favorite_ids = get_favorite_ids(request)
    if page_id in favorite_ids:
        favorite_ids.remove(page_id)
        is_favorite = False
    else:
        favorite_ids.add(page_id)
        is_favorite = True
    request.session[SESSION_KEY] = list(favorite_ids)
    return is_favorite
