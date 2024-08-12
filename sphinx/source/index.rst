.. Dungeon AI documentation master file, created by
   sphinx-quickstart on Mon Jun 17 21:53:44 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

   ######################################
   Welcome to Dungeon AI's documentation!
   ######################################

..
   .. autosummary::
      :toctree: _autosummary
      :template: custom-module-template.rst
      :recursive:
      
      commands

..
   .. toctree::
      :maxdepth: 2
      :caption: Contents:

   .. Indices and tables
   .. ==================

   .. * :ref:`genindex`
   .. * :ref:`modindex`
   .. * :ref:`search`

Commands
========

Below are DungeonAI's commands. The bot relies on slash commands; this means, for example, that you can run help() by typing "/help".

.. 
   _help:

   help
   ****

.. py:function:: help()
   
   `/help` - Lists available commands.

   :return:
      | """
      | **help:** Prints this help menu.
      | **roll [dice] [goal] [private]:** Rolls a die.
      | **link <url> [default] [allguilds]:** Link a character sheet to your user.
      | **view [char]:** View the character sheets that you've linked.
      | **unlink <char>:** Unlink characters from yourself.
      | """

.. 
   _link:

   link
   ****

.. py:function:: link(url,default=True,allguilds=False)

   `/link` - Links a character sheet to your user on this server. If already linked, modifies link settings.

   :param url: The URL or token of your character sheet. (Required)
   :type url: str
   :param default: Set the character sheet as your default character sheet for the current server. (Default: True)
   :type default: bool
   :param allguilds: Make this character sheet accessible from all Discord servers you are in (Default: False)
   :type allguilds: bool
   :return: Message indicating the character ID, guild association status, and default status.

.. 
   _roll:

   roll
   ****

.. py:function:: roll(dice='1d20',goal=None,private=False)

   `/roll` - Default: rolls 1d20. Rolls a number of dice with minimum, maximum, and modifier.

   :param dice: String representing the dice rolled, in format `XdY+Z`, `XdY-Z`, or `XdY`. (Default: 1d20)
   :type dice: str
   :param goal: Value to meet or exceed when rolling. Reports back success/failure if given. (Optional)
   :type goal: int
   :param private: Hide your roll and result from other users. (Default: False)
   :type private: bool
   :return: Message indicating the rolled value and, if a goal was provided, whether it was a success or failure.

.. 
   _unlink:

   unlink
   ******

.. py:function:: unlink(char)

   `/unlink` - Unlink one or more characters from yourself.

   :param char: 'all', 'guild', a character ID, or a comma-separated list of IDs. (Required)
   :type char: str
   :return: Message indicating successfully removed data and data that was requested to be moved but was not present.

.. 
   _view:

   view
   ****

.. py:function:: view(char='guild',private=True)

   `/view` - View a list of your characters.

   :param char: 'all', 'guild', ID,  or comma-separated list of IDs of characters you wish to view. (Default: guild)
   :type char: str
   :param private: Hide the message from other users in this server. (Default: True)
   :type private: bool
   :return: A table of the requested character IDs and their associations.