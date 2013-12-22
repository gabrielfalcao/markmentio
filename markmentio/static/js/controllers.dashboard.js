var APP = angular.module('markmentio', []).
    filter('dashify', function() {
        return function(input) {
            return input.replace("/", "-");
        }
    }).
    filter('length', function() {
        return function(input) {
            return input.length;
        }
    });;

$(function(){
    var ADDRESS = $("body").data("socketaddress");
    var username = $("#socket-meta").data("username");
    var create_hook_ajax_url = $("#dashboard-meta").data("create-hook-ajax-url");
    var context_ajax_url = $("#dashboard-meta").data("context-ajax-url");
    var modal_tracking_ajax_url = $("#dashboard-meta").data("modal-tracking-url");
    function get_modal_url(repository) {
        return modal_tracking_ajax_url.replace(username + "-PLACEHOLDER", repository.name)
    }
    function get_context_ajax_url(owner_name) {
        return context_ajax_url.replace("PLACEHOLDER", owner_name);
    }

    var socket = io.connect(ADDRESS);
    var scope = angular.element($("body")).scope();
    function make_loader(icon_name){
        return '<div class="uk-grid uk-text-center modal-loader"><div class="uk-width-1-1 " style="padding-top: 200px;%"><h2>loading...</h2><i class="uk-icon-'+icon_name+' uk-icon-large uk-icon-spin"></i></div></div>';
    }

    function SelectOrganizationTab (organization) {
        $.getJSON(get_context_ajax_url(organization), function(data){
            scope.$apply(function(){
                scope.repositories[organization] = data.repositories;
                scope.repositories_by_name[organization] = data.repositories_by_name;
                console.log(scope.repositories);
                $(".ajax-loader."+organization).hide();
            });
        });
    };
    function CreateHook (repository) {
        $.post(create_hook_ajax_url, {
            "repository": repository,
            "username": username
        }, function(data){
            scope.$apply(function(){
                var selector = ".row";
                $(selector).each(function(){
                    var $el = $(this);

                    var full_name = $el.data("full-name");
                    if (full_name === repository.full_name) {
                        $el.text(data.url);
                    }
                });

            });
        });
    };
    scope.$apply(function(){
        scope.repositories = {};
        scope.repositories_by_name = {};

        scope.current_project = false;
        scope.username = username;
        scope.SelectOrganizationTab = SelectOrganizationTab;
        scope.CreateHook = CreateHook;
    });
    socket.on('connect', function() {
        console.log('connected');
        socket.emit('listen');
    });
    socket.on('notification', function(data) {
        if (data.notification) {
            humane.log(data.notification.message)
        }
        if (data.log) {
            $("#console").prepend('<code>'+data.log.message+'</code><br />')
        }
        socket.emit('listen');
    });
    socket.on('error', function(e) {
        console.log('error', e);
    });
    socket.on('disconnect', function() {
        console.log('disconnected');
        $(".live-stats-repository").removeClass("active");
        scope.$apply(function(){
            scope.visitors = null;
        });
    });
    $(function(){
    });

});

APP.controller("DashboardController", function($scope){

});
